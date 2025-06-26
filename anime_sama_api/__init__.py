from .top_level import AnimeSama
from .catalogue import Catalogue
from .season import Season
from .episode import Episode, Languages, Players
from .langs import Lang, LangId, lang2ids, id2lang, flags

__package__ = "anime-sama_api"
__all__ = [
    "AnimeSama",
    "Catalogue",
    "Season",
    "Players",
    "Languages",
    "Episode",
    "Lang",
    "LangId",
    "lang2ids",
    "id2lang",
    "flags"
]

__locals = locals()
