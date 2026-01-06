from anime_sama_apis import AnimeSama
import asyncio

api = AnimeSama("anime-sama.fr")

async def main():
    results = await api.search("The Eminence in Shadow", limit=2)
    catalogue = results[0]
    print(f"Name: {catalogue.name}")
    print(f"URL: {catalogue.url}")
    print(f"Image URL: {catalogue.image_url}")
    print(f"Genres: {', '.join(catalogue.genres)}")
    print("-" * 50)

    seasons = await catalogue.seasons()
    if seasons:
        print("=" * 15, "Seasons", "=" * 16)
    season = seasons[1]
    episodes = await season.episodes()
    print(f"Season:             {season.name}")
    print(f"URL:                {season.url}")
    print(f"Number of Episodes: {len(episodes)}")
    i = episodes[0]
    print("Langs:")
    print([a for a in i.languages.availables])
    print("URLS:")
    print([a for a in i.languages.availables.items()])
    print("Best URL:")
    print([a for a in i.consume_player(["VF", "VOSTFR"])])

asyncio.run(main())
