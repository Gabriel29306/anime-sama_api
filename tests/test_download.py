from pathlib import Path
from anime_sama_api.cli.downloader import multi_download, download
from anime_sama_apis.episode import Episode, Languages, Players


def test_multi_download():
    multi_download([Episode({})], Path())


def test_download():
    download(
        Episode(
            Languages(
                {
                    "vf": Players(),
                    "vostfr": Players(
                        [
                            "https://s22.anime-sama.fr/s2/",
                        ]
                    ),
                }
            ),
        ),
        Path(),
        ["VF", "VOSTFR"],
    )
