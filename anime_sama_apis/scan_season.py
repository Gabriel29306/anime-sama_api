from urllib.parse import urlparse

from .scan_episode import ScanEpisode
from .fetcher import Fetcher


class ScanSeason:
    def __init__(
        self,
        url: str,
        name="",
        serie_name="",
        client: Fetcher | None = None,
    ) -> None:
        self.name: str = name
        if not "vf/" in url:
            url += "vf/"
        self.url: str = url
        self.serie_name: str = serie_name
        parsed_url = urlparse(url)
        self.base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        self.client: Fetcher = client or Fetcher(self.base_url)


    async def episodes(self) -> list[ScanEpisode]:
        print(self.url)
        name = self.client.get_html_elem(self.url, "@id=titreOeuvre").inner_html        
        print(f"{self.base_url}/s2/scans/get_nb_chap_et_img.php?oeuvre={name}")
        episodes: dict[str, int] = self.client.get(f"{self.base_url}/s2/scans/get_nb_chap_et_img.php?oeuvre={name}").json()

        return [
            ScanEpisode(
                self.serie_name,
                self.name,
                f"Chapitre {index}",
                int(index),
                length
            )
            for (index, length) in episodes.items()
        ]

    def __repr__(self):
        return f"ScanSeason({self.name!r}, {self.serie_name!r})"

    def __str__(self):
        return f"{self.name} ({self.url})"
