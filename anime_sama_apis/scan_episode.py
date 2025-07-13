from collections.abc import Generator
import re
import logging
from dataclasses import dataclass

from .langs import flags, Lang, LangId, id2lang, lang2ids

logger = logging.getLogger(__name__)


class ScanPlayers(list[str]):
    """Container for scan image URLs for a specific episode/language"""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def __call__(self, index: int) -> Generator[str]:
        """Generate image URLs for this scan episode"""
        yield from self


class ScanLanguages(dict[LangId, ScanPlayers]):
    def __init__(self, *args, **kargs) -> None:
        super().__init__(*args, **kargs)
        if not self:
            logger.warning("No scan images available for %s", self)

    @property
    def availables(self) -> dict[Lang, list[ScanPlayers]]:
        availables: dict[Lang, list[ScanPlayers]] = {}
        for lang_id, scan_players in self.items():
            if availables.get(id2lang[lang_id]) is None:
                availables[id2lang[lang_id]] = []
            availables[id2lang[lang_id]].append(scan_players)
        return availables

    def consume_images(
        self, prefer_languages: list[Lang], index: int
    ) -> Generator[str]:
        # First, try preferred languages
        for prefer_language in prefer_languages:
            for scan_players in self.availables.get(prefer_language, []):
                if scan_players:
                    yield from scan_players(index)
                    return  # Stop after first successful language

        # Fallback to any available language (only first one)
        for language in lang2ids:
            for scan_players in self.availables.get(language, []):
                if scan_players:
                    logger.warning(
                        "Language preference not respected. Using %s", language
                    )
                    yield from scan_players(index)
                    return  # Stop after first successful language


@dataclass(frozen=True)
class ScanEpisode:
    languages: ScanLanguages
    serie_name: str = ""
    season_name: str = ""
    _name: str = ""
    index: int = 1
    length: int = 0

    @property
    def images(self) -> list[str]:
        """Get image URLs for the first available language"""
        # Return images from first available language
        if self.languages:
            first_lang_images = next(iter(self.languages.values()), ScanPlayers())
            return list(first_lang_images)
        
        # Fallback for backward compatibility when no languages are available
        suffix = " " + self.season_name if self.season_name != "Scans" else ""
        return [
            f"https://anime-sama.fr/s2/scans/{self.serie_name}{suffix}/{self.index}/{i}.jpg"
            for i in range(1, self.length + 1)
        ]

    def images_for_lang(self, prefer_languages: list[Lang]) -> list[str]:
        """Get image URLs for specific preferred languages"""
        return list(self.languages.consume_images(prefer_languages, self.index))

    @property
    def name(self) -> str:
        return self._name.strip()

    @property
    def fancy_name(self) -> str:
        return f"{self._name.lstrip()} " + " ".join(
            flags[lang] for lang in self.languages.availables if lang != "VOSTFR"
        )

    @property
    def season_number(self) -> int:
        match_season_number: re.Match[str] | None = re.search(r"\d+", self.season_name)
        return int(match_season_number.group(0)) if match_season_number else 0

    @property
    def long_name(self) -> str:
        return f"{self.season_name} - {self.name}"

    @property
    def short_name(self) -> str:
        return f"{self.serie_name} S{self.season_number:02}E{self.index:02}"

    def consume_images(self, prefer_languages: list[Lang]) -> Generator[str]:
        """Generate image URLs with language preference"""
        yield from self.languages.consume_images(prefer_languages, self.index)

    def best_images(self, prefer_languages: list[Lang]) -> list[str] | None:
        """Get the best image URLs based on language preference"""
        try:
            return list(self.consume_images(prefer_languages))
        except StopIteration:
            return None

    def __str__(self) -> str:
        return self.fancy_name
