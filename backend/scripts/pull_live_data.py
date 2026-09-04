"""
Pull live data once using Finnhub credentials from .env.
"""
import asyncio
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from app.services.ingestion_service import poll_market_data, poll_news

async def main():
    print("Fetching live market quotes from Finnhub...")
    await poll_market_data()
    print("Fetching live company news from Finnhub...")
    await poll_news()
    print("\n[SUCCESS] Live data pull complete!")

if __name__ == "__main__":
    asyncio.run(main())
