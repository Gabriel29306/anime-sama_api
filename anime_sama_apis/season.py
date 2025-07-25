from ast import literal_eval
from dataclasses import dataclass, replace
from functools import reduce
import re
import asyncio
from typing import LiteralString, get_args

from httpx import AsyncClient, Response

from .langs import FlagId, LangId, lang2ids, flagid2lang
from .episode import Episode, Players, Languages
from .utils import remove_some_js_comments, zip_varlen, split_and_strip


@dataclass
class SeasonLangPage:
    lang_id: LangId
    html: str = ""
    episodes_js: str = ""


class Season:
    def __init__(
        self,
        url: str,
        name="",
        serie_name="",
        client: AsyncClient | None = None,
    ) -> None:
        self.url: str = url
        self.site_url: str = "/".join(url.split("/")[:3]) + "/"

        self.name: str = name or url.split("/")[-2]
        self.serie_name: str = serie_name or url.split("/")[-3]

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

    # TODO: Refactor
    def _get_players_from(self, page: SeasonLangPage) -> list[Players]:
        players_list: list[str] = re.findall(
            r"eps(\d+) ?= ?\[([\W\w]+?)\]", remove_some_js_comments(page.episodes_js)
        )
        players_list = sorted(players_list, key=lambda tuple: tuple[0])
        players_list_links = (
            re.findall(r"'(.+?)'", player) for _, player in players_list
        )
        result = []
        invalid_players = [
            "https://vidmoly.to/embed-.html",
            "https://video.sibnet.ru/shell.php?videoid=",
            "https://sendvid.com/embed/",
            "https://vk.com/video_ext.php?oid=&hd=3"
        ]
        
        for players in zip_varlen(*players_list_links):
            if not players:
                continue
            
            # Filtrer les lecteurs invalides en créant une nouvelle liste
            players_c = [player for player in players if player.lower() not in invalid_players]
            
            if not players_c:
                continue
            result.append(Players(players_c))
        return result

    def _get_episodes_names(
        self, page: SeasonLangPage, number_of_episodes: int, number_of_episodes_max: int
    ) -> list[str]:
        functions = re.findall(
            r"resetListe\(\); *[\n\r]+\t*(.*?)}",
            page.html,
            re.DOTALL,
        )[-1]
        functions_list: list[str] = split_and_strip(functions, (";", "\n"))[:-1]

        def padding(n: int) -> LiteralString:
            return " " * (len(str(number_of_episodes_max)) - len(str(n)))

        def episode_name_range(*args) -> list[str]:
            return [f"Episode {n}{padding(n)}" for n in range(*args)]

        episodes_name: list[str] = []
        for function in functions_list:
            if function.startswith("//"):
                continue

            call_start = function.find("(")
            function, args_sting = function[:call_start], function[call_start + 1 : -1]
            if args_sting:
                # Warning literal_eval: Can crash
                args = literal_eval(node_or_string=args_sting + ",")
            else:
                args = ()

            match function:
                case "":
                    continue
                case "creerListe":
                    if len(args) < 2:
                        # Only seen on Dragon Ball GT (Film), Junji Ito Collection (Saison 1) and Orange (Film)
                        # Surely a small oversight in anime-sama.fr
                        # So it is undefined but do nothing is generaly the good reaction
                        continue

                    episodes_name += episode_name_range(int(args[0]), int(args[1]) + 1)
                case "finirListe" | "finirListeOP":
                    if not args:
                        break

                    episodes_name += episode_name_range(
                        int(args[0]),
                        int(args[0]) + number_of_episodes - len(episodes_name),
                    )
                    break
                case "newSP":
                    if not args:
                        raise NotImplementedError(
                            "Error while parsing 'newSP'.\nPlease report this to the developer with the serie + the season you are trying to access."
                        )
                    episodes_name.append(f"Episode {args[0]}")
                case "newSPF":
                    if not args:
                        raise NotImplementedError(
                            "Error while parsing 'newSPF'.\nPlease report this to the developer with the serie + the season you are trying to access."
                        )
                    episodes_name.append(args[0])
                case name:
                    raise NotImplementedError(
                        f"Error cannot parse '{name}'.\nPlease report this to the developer with the serie + the season you are trying to access."
                    )

        return episodes_name

    @staticmethod
    def _extend_episodes(
        current: list[tuple[str, Languages]],
        new: tuple[SeasonLangPage, list[str], list[Players]],
    ) -> list[tuple[str, Languages]]:
        """
        Extend a list of episodes AKA (name, languages) from a list names and players corresponding
        to a language while preserving the relative order of names.
        This function is intended to be used with reduce.
        """
        page: SeasonLangPage 
        names: list[str]
        players_list: list[Players]
        page, names, players_list = new  # Unpack args. This is due to reduce

        fusion: list[tuple[str, Languages]] = []
        curr_done = 0
        for name_new, players in zip(names, players_list):
            for pos, (name_current, languages) in enumerate(current[curr_done:]):
                if name_new == name_current:
                    languages[page.lang_id] = players
                    fusion.extend(current[curr_done : curr_done + pos + 1])
                    curr_done += pos + 1
                    break
            else:
                fusion.append((name_new, Languages({page.lang_id: players})))
        fusion.extend(current[curr_done:])
        return fusion

    async def episodes(self) -> list[Episode]:
        pages: list[SeasonLangPage] = await self.get_all_pages()

        players_list: list[list[Players]] = [self._get_players_from(page) for page in pages]

        number_of_episodes_max = max(
            len(episodes_page) for episodes_page in players_list
        )

        episodes_names = [
            self._get_episodes_names(page, len(episodes_page), number_of_episodes_max)
            for page, episodes_page in zip(pages, players_list)
        ]

        episodes: list[tuple[str, Languages]] = reduce(
            self._extend_episodes, zip(pages, episodes_names, players_list), []
        )

        return [
            Episode(
                languages,
                self.serie_name,
                self.name,
                name,
                index,
            )
            for index, (name, languages) in enumerate(episodes, start=1)
        ]

    def __repr__(self):
        return f"Season({self.name!r}, {self.serie_name!r})"

    def __str__(self):
        return self.name

    def __eq__(self, value):
        return self.url == value.url
