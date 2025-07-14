import asyncio
from collections.abc import AsyncIterator, Generator
from typing import Literal, TypeAlias
from urllib.parse import quote_plus
import logging
import re

from httpx import AsyncClient, Response

from .langs import Lang
from .utils import filter_literal, fix_categories
from .catalogue import Catalogue, Category

SearchLangs: TypeAlias = Literal["VOSTFR", "VASTFR", "VF"]

logger = logging.getLogger(__name__)


class AnimeSama:
    def __init__(self, site_url: str, client: AsyncClient | None = None) -> None:
        if not site_url.startswith("http"):
            site_url = f"https://{site_url}"
        if not site_url.endswith("/"):
            site_url += "/"
        self.site_url: str = site_url
        self.client: AsyncClient = client or AsyncClient()

    def _yield_catalogues_from(self, html: str) -> Generator[Catalogue]:
        text_without_script: str = re.sub(r"<script.+?</script>", "", html)
        for match in re.finditer(
            rf"href=\"({self.site_url}catalogue/.+)\"[\W\w]+?src=\"(.+)\"[\W\w]+?>(.*)\n?<[\W\w]+?>(.*)\n?<[\W\w]+?>(.*)\n?<[\W\w]+?>(.*)\n?<[\W\w]+?>(.*)\n?<",
            text_without_script,
        ):
            url, image_url, name, alternative_names, genres, categories, languages = (
                match.groups()
            )
            alternative_names = (
                alternative_names.split(", ") if alternative_names else []
            )
            genres = genres.split(", ") if genres else []
            categories = categories.split(", ") if categories else []
            languages = languages.split(", ") if languages else []

            def not_in_literal(value) -> None:
                logger.warning(
                    f"Error while parsing '{value}'. \nPlease report this to the developer with the serie you are trying to access."
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

        response: Response = await self.client.get(query_url)
        response.raise_for_status()

        try:
            last_page: int = int(re.findall(r"page=(\d+)", response.text)[-1])
        except IndexError:
            return [] # No results found

        if limit is not None:
            # There is a max of 48 results per pages
            last_page = min((limit // 48) + 1 if limit % 48 else (limit // 48), last_page)

        responses: list[Response] = [response] + await asyncio.gather(
            *(
                self.client.get(f"{self.site_url}catalogue/?search={query}&page={num}{suffix}")
                for num in range(2, last_page + 1)
            )
        )

        catalogues: list[Catalogue] = []
        for response in responses:
            if not response.is_success:
                continue

            catalogues += list(self._yield_catalogues_from(response.text))

        return catalogues[:limit] if limit else catalogues

    async def search_iter(self, query: str) -> AsyncIterator[Catalogue]:
        response: Response = (
            await self.client.get(f"{self.site_url}catalogue/?search={query}")
        ).raise_for_status()

        try:
            last_page = int(re.findall(r"page=(\d+)", response.text)[-1])
        except IndexError:
            return # No results found

        for catalogue in self._yield_catalogues_from(response.text):
            yield catalogue

        for number in range(2, last_page + 1):
            response = await self.client.get(
                f"{self.site_url}catalogue/?search={query}&page={number}"
            )

            if not response.is_success:
                continue

            for catalogue in self._yield_catalogues_from(response.text):
                yield catalogue

    async def catalogues_iter(self) -> AsyncIterator[Catalogue]:
        async for catalogue in self.search_iter(""):
            yield catalogue

    async def all_catalogues(self) -> list[Catalogue]:
        return await self.search("")
