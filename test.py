from research_bot.manager import ResearchManager
import asyncio

async def main() -> None:
    query = input("What would you like to research? ")
    await ResearchManager().run(query)
 
if __name__ == "__main__":
    asyncio.run(main())
