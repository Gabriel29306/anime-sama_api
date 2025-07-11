from anime_sama_apis import AnimeSama
import asyncio

api = AnimeSama("anime-sama.fr")

async def main():
    results = await api.search("")
    for catalogue in results:
        #s = await catalogue.synopsis()
        if True:
            continue
        print(f"Name: {catalogue.name}")
        print(f"URL: {catalogue.url}")
        print(f"Image URL: {catalogue.image_url}")
        print(f"Genres: {', '.join(catalogue.genres)}")
        print(f"Synopsis: {s}")
        print(f"Categories: {', '.join(catalogue.categories)}")
        print(f"Languages: {', '.join(map(str, catalogue.languages))}")
        print("-" * 40)

    catalogue = results[0]
    seasons = await catalogue.seasons()
    for season in seasons:
        episodes = await season.episodes()
        print(f"Season: {season.name}")
        print(f"URL: {season.url}")
        print(f"Number of Episodes: {len(episodes)}")
        print("-" * 40)

asyncio.run(main())
