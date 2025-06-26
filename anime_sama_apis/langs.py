from typing import Literal


Lang = Literal["VASTFR", "VCN", "VF", "VJSTFR", "VKR", "VQC", "VOSTFR"]
LangId = Literal["va", "vcn", "vf", "vf1", "vf2", "vj", "vkr", "vqc", "vostfr"]
FlagId = Literal["cn", "qc", "en", "pal", "kr", "fr", "jp"]

lang2ids: dict[Lang, list[LangId]] = {
    "VOSTFR": ["vostfr"],
    "VASTFR": ["va"],
    "VCN": ["vcn"],
    "VF": ["vf", "vf1", "vf2"],
    "VJSTFR": ["vj"],
    "VKR": ["vkr"],
    "VQC": ["vqc"],
}

id2lang: dict[LangId, Lang] = {
    lang_id: lang for lang, langs_id in lang2ids.items() for lang_id in langs_id
}

flags: dict[Lang | LangId, str] = {
    "VOSTFR": "",
    "VASTFR": "🇬🇧",
    "VCN": "🇨🇳",
    "VF": "🇫🇷",
    "VJSTFR": "🇯🇵",
    "VKR": "🇰🇷",
    "VQC": "🏴󠁣󠁡󠁱󠁣󠁿",
}

flagid2lang: dict[FlagId, Lang] = {
    "cn": "VCN",
    "qc": "VQC",
    "en": "VASTFR",
    "kr": "VKR",
    "fr": "VF",
    "jp": "VJSTFR",
}

for language, language_ids in lang2ids.items():
    for lang_id in language_ids:
        flags[lang_id] = flags[language]
