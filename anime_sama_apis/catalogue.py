import re
from typing import Literal

from httpx import AsyncClient

from anime_sama_apis.langs import Lang

from .utils import remove_some_js_comments, unescape
from .season import Season
from .scan_season import ScanSeason
from .langs import flags


Category = Literal["Anime", "Scans", "Film", "Autres"]


class Catalogue:
    def __init__(
        self,
        url: str,
        name="",
        alternative_names: list[str] | None = None,
        genres: list[str] | None = None,
        categories: list[Category] | None = None,
        languages: list[Lang] | None = None,
        image_url="",
        client: AsyncClient | None = None,
    ) -> None:
        if alternative_names is None:
            alternative_names = []
        if genres is None:
            genres = []
        if categories is None:
            categories = []
        if languages is None:
            languages = []

        self.url = url + "/" if url[-1] != "/" else url
        self.site_url: str = "/".join(url.split("/")[:3]) + "/"
        self.client: AsyncClient = client or AsyncClient()

        self.name: str = unescape(name or url.split("/")[-2])

        self._page: str | None = None
        self.alternative_names: list[str] = [unescape(name) for name in alternative_names]
        self.genres: list[str] = [unescape(genre) for genre in genres]
        self.categories: list[Category] = categories
        self.languages: list[Lang] = languages
        self.image_url: str = image_url

    async def page(self) -> str:
        if self._page is not None:
            return self._page

        response = await self.client.get(self.url)

        if not response.is_success:
            self._page = ""
        else:
            self._page = response.text

        return self._page

    async def seasons(self) -> list[Season]:
        page_without_comments: str = remove_some_js_comments(string=await self.page())

        seasons = re.findall(
            r'panneauAnime\("(.+?)", *"(.+?)(?:vostfr|vf)"\);', page_without_comments
        )

        seasons = [
            Season(
                url=self.url + link,
                name=name,
                serie_name=self.name,
                client=self.client,
            )
            for name, link in seasons
        ]

        return seasons

    async def scans_seasons(self) -> list[ScanSeason]:
        page_without_comments: str = remove_some_js_comments(string=await self.page())

        seasons = re.findall(
            r'panneauScan\("(.+?)", *"(.+?)(?:vostfr|vf)"\);', page_without_comments
        )

        seasons = [
            ScanSeason(
                url=self.url + link,
                name=name,
                serie_name=self.name,
                client=self.client,
            )
            for name, link in seasons
        ]

        return seasons


    async def advancement(self) -> str:
        search = re.findall(r"Avancement.+?>(.+?)<", await self.page())

        if not search:
            return ""

        return search[0]

    async def correspondence(self) -> str:
        search = re.findall(r"Correspondance.+?>(.+?)<", await self.page())

        if not search:
            return ""

        return search[0]

    async def synopsis(self) -> str:
        search: list[str] = re.findall(r"Synopsis.*?<p.*?>(.+?)</p>", await self.page(), re.DOTALL)

        if not search:
            return ""

        return search[0]

    @property
    def is_anime(self) -> bool:
        return "Anime" in self.categories

    @property
    def is_manga(self) -> bool:
        return "Scans" in self.categories

    @property
    def is_film(self) -> bool:
        return "Film" in self.categories

    @property
    def is_other(self) -> bool:
        return "Autres" in self.categories

    @property
    def fancy_name(self):
        names = [""] + self.alternative_names if self.alternative_names else []
        return f"{self.name}[bright_black]{' - '.join(names)} {' '.join(flags[lang] for lang in self.languages if lang != 'VOSTFR')}"

    def __repr__(self):
        return f"Catalogue({self.url!r}, {self.name!r})"

    def __str__(self):
        return self.fancy_name

    def __eq__(self, value):
        return self.url == value.url
