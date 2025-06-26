import asyncio
from anime_sama_apis import main, AnimeSama
from anime_sama_api.cli.utils import print_selection
from rich import print


async def async_main():
    catalogues = await AnimeSama("https://anime-sama.fr/").all_catalogues()
    c_seasons = await asyncio.gather(*(catalogue.seasons() for catalogue in catalogues))

    for seasons in c_seasons:
        if not seasons:
            continue

        print(f"[blue][underline]{seasons[0].serie_name}")
        for season in seasons:
            print(f"    [blue]{season.name}")
            episodes = await season.episodes()
            print_selection(episodes, exit=False)


if __name__ == "__main__":
    main()

    # asyncio.run(async_main())
