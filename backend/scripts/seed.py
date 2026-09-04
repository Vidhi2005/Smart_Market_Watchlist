"""
Seed script — creates one demo user and 10 well-known symbols.
Usage:  python scripts/seed.py
Requires DATABASE_URL env var (or copy .env.example → .env first).
"""
import asyncio
import os
import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg
from dotenv import load_dotenv
import uuid as _uuid

from app.auth.security import hash_password  # noqa: E402

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

DEMO_USER_ID = _uuid.UUID("00000000-0000-0000-0000-000000000001")
DEMO_PASSWORD = "demo12345"  # login: demo@smartwatchlist.dev / demo12345


SYMBOLS = [
    # ── US Markets (via Finnhub) ───────────────────────────────────────────────
    ("AAPL",  "Apple Inc.",                  "Technology",       "NASDAQ"),
    ("MSFT",  "Microsoft Corporation",        "Technology",       "NASDAQ"),
    ("NVDA",  "NVIDIA Corporation",           "Technology",       "NASDAQ"),
    ("GOOGL", "Alphabet Inc.",                "Technology",       "NASDAQ"),
    ("AMZN",  "Amazon.com Inc.",              "Consumer Cyclical","NASDAQ"),
    ("TSLA",  "Tesla Inc.",                   "Consumer Cyclical","NASDAQ"),
    ("META",  "Meta Platforms Inc.",          "Technology",       "NASDAQ"),
    ("JPM",   "JPMorgan Chase & Co.",         "Financial",        "NYSE"),
    ("SPY",   "SPDR S&P 500 ETF Trust",      "ETF",              "NYSE"),
    ("QQQ",   "Invesco QQQ Trust",            "ETF",              "NASDAQ"),

    # ── Indian Markets / NSE (via Yahoo Finance — free, no key needed) ────────
    # Suffix .NS = NSE  |  .BO = BSE
    ("RELIANCE.NS",   "Reliance Industries Ltd.",       "Energy",           "NSE"),
    ("TCS.NS",        "Tata Consultancy Services Ltd.", "Technology",       "NSE"),
    ("INFY.NS",       "Infosys Ltd.",                   "Technology",       "NSE"),
    ("HDFCBANK.NS",   "HDFC Bank Ltd.",                 "Financial",        "NSE"),
    ("ICICIBANK.NS",  "ICICI Bank Ltd.",                "Financial",        "NSE"),
    ("WIPRO.NS",      "Wipro Ltd.",                     "Technology",       "NSE"),
    ("HINDUNILVR.NS", "Hindustan Unilever Ltd.",        "Consumer Staples", "NSE"),
    ("BAJFINANCE.NS", "Bajaj Finance Ltd.",             "Financial",        "NSE"),
    ("SBIN.NS",       "State Bank of India",            "Financial",        "NSE"),
    ("ADANIENT.NS",   "Adani Enterprises Ltd.",         "Industrials",      "NSE"),
    ("NIFTY50.NS",    "Nifty 50 Index",                 "Index",            "NSE"),
]


async def main() -> None:
    raw_url = os.environ["DATABASE_URL"]
    # asyncpg wants postgresql:// not postgresql+asyncpg://
    dsn = raw_url.replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(dsn)
    try:
        # Run schema first
        schema_path = Path(__file__).parent / "schema.sql"
        schema_sql = schema_path.read_text()
        await conn.execute(schema_sql)
        print("[OK] Schema applied.")

        # Insert demo user (idempotent) — also backfills password_hash for a
        # pre-existing row from before auth existed, so it stays loggable.
        await conn.execute(
            """
            INSERT INTO users (id, email, display_name, password_hash)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (id) DO UPDATE
              SET password_hash = COALESCE(users.password_hash, EXCLUDED.password_hash)
            """,
            DEMO_USER_ID,
            "demo@smartwatchlist.dev",
            "Demo Trader",
            hash_password(DEMO_PASSWORD),
        )
        print(f"[OK] Demo user seeded: {DEMO_USER_ID}  (login: demo@smartwatchlist.dev / {DEMO_PASSWORD})")

        # Insert symbols (idempotent)
        for sym, name, sector, exchange in SYMBOLS:
            await conn.execute(
                """
                INSERT INTO symbols (symbol, company_name, sector, exchange)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (symbol) DO UPDATE
                  SET company_name = EXCLUDED.company_name,
                      sector       = EXCLUDED.sector,
                      exchange     = EXCLUDED.exchange
                """,
                sym, name, sector, exchange,
            )
        print(f"[OK] {len(SYMBOLS)} symbols seeded.")

        # Create default watchlist for demo user (idempotent via name+user)
        wl_id = await conn.fetchval(
            """
            INSERT INTO watchlists (user_id, name)
            VALUES ($1, 'My Watchlist')
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            DEMO_USER_ID,
        )
        if wl_id is None:
            wl_id = await conn.fetchval(
                "SELECT id FROM watchlists WHERE user_id = $1 LIMIT 1",
                DEMO_USER_ID,
            )
        print(f"[OK] Default watchlist: {wl_id}")

        # Add first 5 symbols to watchlist
        for sym, *_ in SYMBOLS[:5]:
            sym_id = await conn.fetchval(
                "SELECT id FROM symbols WHERE symbol = $1", sym
            )
            await conn.execute(
                """
                INSERT INTO watchlist_items (watchlist_id, symbol_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
                """,
                wl_id, sym_id,
            )
        print("[OK] Added AAPL, MSFT, NVDA, GOOGL, AMZN to default watchlist.")

        print("\nSeed complete!")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
