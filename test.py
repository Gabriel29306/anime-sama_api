from anime_sama_apis import AnimeSama
import asyncio

api = AnimeSama("anime-sama.fr")

async def main():
    results = await api.search("Solo Leveling", limit=2)
    for catalogue in results:
        s = await catalogue.synopsis()
        print(f"Name: {catalogue.name}")
        print(f"URL: {catalogue.url}")
        print(f"Image URL: {catalogue.image_url}")
        print(f"Genres: {', '.join(catalogue.genres)}")
        print(f"Synopsis: {s}")
        print(f"Categories: {', '.join(catalogue.categories)}")
        print(f"Languages: {', '.join(map(str, catalogue.languages))}")
        print("-" * 50)

        seasons = await catalogue.seasons()
        if seasons:
            print("=" * 40)
            print("=" * 15, "Seasons", "=" * 16)
            print("=" * 40)
        for season in seasons:
            episodes = await season.episodes()
            print(f"Season:             {season.name}")
            print(f"URL:                {season.url}")
            print(f"Number of Episodes: {len(episodes)}")
            print("-" * 60)

        seasons = await catalogue.scans_seasons()
        if seasons:
            print("=" * 40)
            print("=" * 16, "Scans", "=" * 17)
            print("=" * 40)
        for season in seasons:
            episodes = await season.episodes()
            print(f"Season:             {season.name}")
            print(f"URL:                {season.url}")
            print(f"Number of Episodes: {len(episodes)}")
            print("-" * 60)

asyncio.run(main())
