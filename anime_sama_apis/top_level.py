import asyncio
from collections.abc import AsyncIterator, Generator
from typing import Literal, TypeAlias
from urllib.parse import quote_plus, urlparse
import logging
import re

from DrissionPage import ChromiumOptions, WebPage
from requests import Response

from .langs import Lang
from .utils import filter_literal, fix_categories
from .catalogue import Catalogue, Category

from .fetcher import Fetcher

SearchLangs: TypeAlias = Literal["VOSTFR", "VASTFR", "VF"]

logger = logging.getLogger(__name__)


catalogue_pattern = re.compile(
    r"<div[^>]*class=\"[^\"]*catalog-card[^\"]*\"[^>]*>.*?"
    r"<a\s+href=\"(?P<url>[^\"]+)\".*?"
    r"<img[^>]*src=\"(?P<image_url>[^\"]+)\".*?"
    r"<h2 class=\"card-title\">\s*(?P<name>[^<]*)\s*</h2>.*?"
    r"<p class=\"alternate-titles\">\s*(?P<alternative_names>[^<]*)\s*</p>.*?"
    r"Genres\s*</span>\s*<div class=\"genre-tags\">(?P<genres>.*?)</div>.*?"
    r"Types\s*</span>.*?<p class=\"info-value\">\s*(?P<categories>[^<]*)\s*</p>.*?"
    r"Langues\s*</span>\s*<div class=\"lang-flags\">(?P<languages>.*?)</div>",
    re.DOTALL | re.IGNORECASE
)

class AnimeSama:
    def __init__(
            self,
            site_url: str,
            client: WebPage | None = None,
            client_options: ChromiumOptions | None = None
        ) -> None:
        if not site_url.startswith("http"):
            site_url = f"https://{site_url}"
        self.tld = "." + urlparse(site_url).netloc.split(".")[-1]
        if not site_url.endswith("/"):
            site_url += "/"
        self.site_url: str = site_url
        self.client = Fetcher(site_url, client, client_options)


    def _yield_catalogues_from(self, html: str) -> Generator[Catalogue]:
        text_without_script: str = re.sub(r"<script.+?</script>", "", html)

        for match in catalogue_pattern.finditer(text_without_script):
            url = match.group("url")
            image_url = match.group("image_url")
            name = match.group("name")
            alt_names_raw = match.group("alternative_names")
            genres_raw = match.group("genres")
            categories_raw = match.group("categories")
            languages_raw = match.group("languages")

            if (tld := urlparse(url).netloc.split(".")[-1]) != self.tld[1:]:
                url = url.replace("." + tld, self.tld)

            alternative_names = (
                alt_names_raw.split(", ") if alt_names_raw else []
            )

            genres = re.findall(r">([^<]+)</span>", genres_raw) if genres_raw else []

            categories = categories_raw.split(", ") if categories_raw else []

            languages = re.findall(r"title=\"([^\"]+)\"", languages_raw) if languages_raw else []

            def not_in_literal(value) -> None:
                logger.warning(
                    f"Error while parsing \"{value}\". \nPlease report this to the developer with the serie you are trying to access."
                )

            categories = fix_categories(categories)
            categories_checked: list[Category] = filter_literal(
                categories, Category, not_in_literal
            )  # type: ignore
            languages_checked: list[Lang] = filter_literal(
                languages, Lang, not_in_literal
            )  # type: ignore

            yield Catalogue(
                url=url.strip(),
                name=name,
                alternative_names=alternative_names,
                genres=genres,
                categories=categories_checked,
                languages=languages_checked,
                image_url=image_url,
                client=self.client,
            )


    async def search(self, query: str, types: list[Category] = [], langs: list[SearchLangs] = [], limit: int | None = None) -> list[Catalogue]:
        suffix: str = ""

        for type in types:
            suffix += f"&type[]={type}"
        for lang in langs:
            suffix += f"&lang[]={lang}"
        query_url: str = f"{self.site_url}catalogue/?search={quote_plus(query)}{suffix}"

        response: Response = await asyncio.to_thread(self.client.get, query_url)
        response.raise_for_status()

        try:
            last_page: int = int(re.findall(r"page=(\d+)", response.text)[-1])
        except IndexError:
            last_page: int = 1

        if limit is not None:
            # There is a max of 48 results per pages
            last_page = min((limit // 48) + 1 if limit % 48 else (limit // 48), last_page)

        responses: list[Response] = [response] + await asyncio.gather(
            *(
                asyncio.to_thread(self.client.get, f"{self.site_url}catalogue/?search={query}&page={num}{suffix}")
                for num in range(2, last_page + 1)
            )
        )

        catalogues: list[Catalogue] = []
        for response in responses:
            if not response.ok:
                continue

            catalogues += list(self._yield_catalogues_from(response.text))

        return catalogues[:limit] if limit else catalogues

    async def search_iter(self, query: str) -> AsyncIterator[Catalogue]:
        response: Response = (
            await asyncio.to_thread(self.client.get, f"{self.site_url}catalogue/?search={query}")
        )
        response.raise_for_status()

        try:
            last_page = int(re.findall(r"page=(\d+)", response.text)[-1])
        except IndexError:
            return # No results found

        for catalogue in self._yield_catalogues_from(response.text):
            yield catalogue

        for number in range(2, last_page + 1):
            response = await asyncio.to_thread(self.client.get,
                f"{self.site_url}catalogue/?search={query}&page={number}"
            )

            if not response.ok:
                continue

            for catalogue in self._yield_catalogues_from(response.text):
                yield catalogue

    async def catalogues_iter(self) -> AsyncIterator[Catalogue]:
        async for catalogue in self.search_iter(""):
            yield catalogue

    async def all_catalogues(self) -> list[Catalogue]:
        return await self.search("")
