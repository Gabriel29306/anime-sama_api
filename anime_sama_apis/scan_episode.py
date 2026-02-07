import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class ScanEpisode:
    serie_name: str = ""
    season_name: str = ""
    _name: str = ""
    index: int = 1
    length: int = 0

    @property
    def images(self) -> list[str]:
        """Get image URLs for the first available language"""        
        # Fallback for backward compatibility when no languages are available
        suffix = " " + self.season_name if self.season_name != "Scans" else ""
        return [
            f"https://anime-sama.fr/s2/scans/{self.serie_name}/{self.index}/{i}.jpg"
            for i in range(1, self.length + 1)
        ]
    @property
    def name(self) -> str:
        return self._name.strip()

    @property
    def fancy_name(self) -> str:
        return f"{self._name.lstrip()}"

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

    def __str__(self) -> str:
        return self.fancy_name
