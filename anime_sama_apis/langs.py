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


if __name__ == "__main__":
    import re
    import asyncio
    from pprint import pprint

    import httpx

    from anime_sama_apis.top_level import AnimeSama

    SCRIPT_VIDEO_URL = "https://anime-sama.fr/js/contenu/script_videos.js"
    page = httpx.get(SCRIPT_VIDEO_URL).text
    langs = {}

    matchs = re.findall(r"if\((.+)\){langue = \"(.+)\";}", page)
    for match in matchs:
        langs[match[1]] = match[0].split('"')[1::2]

    pprint(langs)

    async def main():
        async for catalogue in AnimeSama("https://anime-sama.fr/").catalogues_iter():
            if await catalogue.seasons():
                break
        else:
            raise

        vostfr_url = (await catalogue.seasons())[0].url + "vostfr/"
        response = await catalogue.client.get(vostfr_url)
        if not response.is_success:
            raise
        print(set(re.findall(r"src=\".+flag_(.+?)\.png\"", response.text)))

    asyncio.run(main())
