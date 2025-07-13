from dataclasses import dataclass, replace
import re
import asyncio
from functools import reduce
from typing import get_args

from httpx import AsyncClient, Response

from .langs import FlagId, LangId, lang2ids, flagid2lang
from .scan_episode import ScanEpisode, ScanLanguages, ScanPlayers
from .utils import remove_some_js_comments

@dataclass
class SeasonLangPage:
    lang_id: LangId
    html: str = ""
    episodes_js: str = ""

class ScanSeason:
    def __init__(
        self,
        url: str,
        name="",
        serie_name="",
        client: AsyncClient | None = None,
    ) -> None:
        self.name: str = name
        self.url: str = url
        self.serie_name: str = serie_name
        self.client: AsyncClient = client or AsyncClient()

    async def get_all_pages(self) -> list[SeasonLangPage]:
        async def process_page(lang_id: LangId) -> SeasonLangPage:
            page_url: str = self.url + lang_id + "/"
            response: Response = await self.client.get(page_url)
            if not response.is_success:
                return SeasonLangPage(lang_id=lang_id)
            html: str = response.text
            match_url: re.Match[str] | None = re.search(r"episodes\.js\?filever=\d+", html)

            if not match_url:
                return SeasonLangPage(lang_id=lang_id)

            episodes_js: Response = await self.client.get(page_url + match_url.group(0))
            if not episodes_js.is_success:
                return SeasonLangPage(lang_id=lang_id)

            return SeasonLangPage(
                lang_id=lang_id, html=html, episodes_js=episodes_js.text
            )

        pages: list[SeasonLangPage] = await asyncio.gather(
            *(process_page(lang_id) for lang_id in get_args(LangId)),
            return_exceptions=False
        )
        pages_dict: dict[str, SeasonLangPage] = {page.lang_id: page for page in pages}
        if pages_dict["vostfr"].html:
            flag_id_vo: FlagId = re.findall(
                r"src=\".+flag_(.+?)\.png\".*?[\n\t]*<p.*?>VO</p>",
                remove_some_js_comments(pages_dict["vostfr"].html),
            )[0]

            for lang_id in lang2ids[flagid2lang[flag_id_vo]]:
                if not pages_dict[lang_id].html:
                    pages_dict[lang_id] = replace(pages_dict["vostfr"])
                    pages_dict[lang_id].lang_id = lang_id
                    break

        return [value for value in pages_dict.values() if value.html]

    def _get_scan_players_from(self, page: SeasonLangPage) -> list[ScanPlayers]:
        """Extract scan images URLs from episodes.js for a specific language page"""
        match_episodes: list[tuple[str, str]] = re.findall(
            r"var eps(\d+) ?= ?(\[[^\]]*\]);", page.episodes_js, re.DOTALL
        )
        if not match_episodes:
            return []

        match_force_length = re.findall(
            r"eps(\d+)\.length ?= ?(\d+);", page.episodes_js, re.DOTALL
        )

        forced_length: dict[int, int] = {}
        for force in match_force_length:
            episode_number: int = int(force[0])
            episode_length: int = int(force[1])
            forced_length[episode_number] = episode_length

        scan_players_list: list[ScanPlayers] = []
        
        for match in match_episodes:
            episode_number: int = int(match[0])
            episode_urls: str = match[1]
            episodes_list: list[str] = eval(episode_urls)
            episodes_count = forced_length.get(episode_number, len(episodes_list))
            
            # Always generate anime-sama.fr URLs for scans
            # Google Drive URLs are not useful, we need the direct scan URLs
            suffix = " " + self.name if self.name != "Scans" else ""
            image_urls = [
                f"https://anime-sama.fr/s2/scans/{self.serie_name}{suffix}/{episode_number}/{i}.jpg"
                for i in range(1, episodes_count + 1)
            ]
            
            scan_players_list.append(ScanPlayers(image_urls))

        return scan_players_list

    @staticmethod
    def _extend_episodes(
        current: list[tuple[str, ScanLanguages]],
        new: tuple[SeasonLangPage, list[ScanPlayers], str],  # Added season_name
    ) -> list[tuple[str, ScanLanguages]]:
        """
        Extend a list of episodes AKA (name, languages) from scan_players corresponding
        to a language while preserving the relative order of names.
        This function is intended to be used with reduce.
        """
        page: SeasonLangPage 
        scan_players_list: list[ScanPlayers]
        season_name: str
        page, scan_players_list, season_name = new  # Unpack args. This is due to reduce

        fusion: list[tuple[str, ScanLanguages]] = []
        
        for index, scan_players in enumerate(scan_players_list, start=1):
            episode_name = f"{season_name} - Épisode {index}"
            
            # Look for existing episode with same name
            found = False
            for pos, (name_current, languages) in enumerate(current):
                if episode_name == name_current:
                    languages[page.lang_id] = scan_players
                    found = True
                    break
            
            if not found:
                # Create new episode entry
                fusion.append((episode_name, ScanLanguages({page.lang_id: scan_players})))
        
        # Add any remaining episodes from current that weren't matched
        for name_current, languages in current:
            if not any(name_current == name for name, _ in fusion):
                fusion.append((name_current, languages))
        
        return fusion

    async def episodes(self) -> list[ScanEpisode]:
        pages: list[SeasonLangPage] = await self.get_all_pages()

        scan_players_list: list[list[ScanPlayers]] = [self._get_scan_players_from(page) for page in pages]

        # Use reduce to merge episodes from different languages
        episodes: list[tuple[str, ScanLanguages]] = reduce(
            self._extend_episodes, 
            [(page, players, self.name) for page, players in zip(pages, scan_players_list)], 
            []
        )

        return [
            ScanEpisode(
                languages,
                self.serie_name,
                self.name,
                name,
                index,
                # Calculate length from first available language
                len(next(iter(languages.values()), [])) if languages else 0,
            )
            for index, (name, languages) in enumerate(episodes, start=1)
        ]

    def __repr__(self):
        return f"ScanSeason({self.name!r}, {self.serie_name!r})"

    def __str__(self):
        return f"{self.name} ({self.url})"
