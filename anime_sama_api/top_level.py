import asyncio
from collections.abc import AsyncIterator, Generator
from typing import Literal
from urllib.parse import quote_plus
import logging
import re

from httpx import AsyncClient

from .langs import Lang
from .utils import filter_literal
from .catalogue import Catalogue, Category

type SearchType = Literal["Anime"] | Literal["Film"] | Literal["Scans"] | Literal["Autres"]
type SearchLangs = Literal["VOSTFR", "VASTFR", "VF"]

logger = logging.getLogger(__name__)


class AnimeSama:
    def __init__(self, site_url: str, client: AsyncClient | None = None) -> None:
        if not site_url.startswith("http"):
            site_url = f"https://{site_url}"
        self.site_url = site_url
        self.client = client or AsyncClient()

    def _yield_catalogues_from(self, html: str) -> Generator[Catalogue]:
        text_without_script = re.sub(r"<script.+?</script>", "", html)
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

            def not_in_literal(value):
                logger.warning(
                    f"Error while parsing '{value}'. \nPlease report this to the developer with the serie you are trying to access."
                )

            categories_checked: list[Category] = filter_literal(
                categories, Category, not_in_literal
            )  # type: ignore
            languages_checked: list[Lang] = filter_literal(
                languages, Lang, not_in_literal
            )  # type: ignore

            yield Catalogue(
                url=url,
                name=name,
                alternative_names=alternative_names,
                genres=genres,
                categories=categories_checked,
                languages=languages_checked,
                image_url=image_url,
                client=self.client,
            )

    async def search(self, query: str, types: list[SearchType] = [], langs: list[SearchLangs] = []) -> list[Catalogue]:
        suffix = ""
        for type in types:
            suffix += f"&type[]={type}"
        for lang in langs:
            suffix += f"&lang[]={lang}"
        query_url = f"{self.site_url}catalogue/?search={quote_plus(query)}{suffix}"
        response = (
            await self.client.get(query_url)
        ).raise_for_status()

        last_page = int(re.findall(r"page=(\d+)", response.text)[-1])

        responses = [response] + await asyncio.gather(
            *(
                self.client.get(f"{self.site_url}catalogue/?search={query}&page={num}")
                for num in range(2, last_page + 1)
            )
        )

        catalogues = []
        for response in responses:
            if not response.is_success:
                continue

            catalogues += list(self._yield_catalogues_from(response.text))

        return catalogues

    async def search_iter(self, query: str) -> AsyncIterator[Catalogue]:
        response = (
            await self.client.get(f"{self.site_url}catalogue/?search={query}")
        ).raise_for_status()

        last_page = int(re.findall(r"page=(\d+)", response.text)[-1])

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
