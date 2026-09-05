"""
Benchmark for GET /api/watchlists/{id}/changes at the service level.

Measures attention_service.get_changes() directly (not over HTTP, to isolate
backend computation from network/uvicorn overhead) for watchlists of 5, 20,
50, and 100 symbols. Seeds synthetic-but-realistic data by direct DB writes
(same pattern as demo_service.py) — no provider or LLM calls happen during
seeding OR during the timed reads, because that's the entire point being
measured: the user-facing read path should be pure Postgres + Python.

Usage:
    python scripts/benchmark_changes.py

Cleans up everything it creates when done.
"""
import asyncio
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    MarketEvent,
    MarketSnapshot,
    Symbol,
    User,
    UserObservation,
    Watchlist,
    WatchlistItem,
)
from app.services import attention_service  # noqa: E402

BENCH_USER_EMAIL = "benchmark@internal.local"
WATCHLIST_SIZES = [5, 20, 50, 100]
ITERATIONS_PER_SIZE = 5


async def _seed(db, n: int) -> tuple[str, str, list[str]]:
    """Creates a benchmark user, a watchlist, and n symbols each with a real
    snapshot + a real, already-scored/explained MarketEvent (template
    explanation — a pure function, no LLM call during seeding)."""
    from app.llm.fallback import template_explanation

    user = User(
        id=str(uuid.uuid4()),
        email=f"{BENCH_USER_EMAIL}.{uuid.uuid4().hex[:8]}",
        display_name="Benchmark",
        password_hash=None,
    )
    db.add(user)
    await db.flush()

    wl = Watchlist(user_id=user.id, name="Benchmark Watchlist")
    db.add(wl)
    await db.flush()

    now = datetime.now(tz=timezone.utc)
    symbol_ids = []

    for i in range(n):
        sym = Symbol(
            symbol=f"BENCH{i}",
            company_name=f"Benchmark Co {i}",
            sector="Technology",
            exchange="NASDAQ",
        )
        db.add(sym)
        await db.flush()
        symbol_ids.append(sym.id)

        db.add(WatchlistItem(watchlist_id=wl.id, symbol_id=sym.id))

        # A few daily bars so avg-volume/breakout have real data to read.
        for d in range(5, 0, -1):
            db.add(MarketSnapshot(
                symbol_id=sym.id,
                price=Decimal("100.00"),
                volume=1_000_000,
                previous_close=Decimal("100.00"),
                open=Decimal("100.00"),
                high=Decimal("101.00"),
                low=Decimal("99.00"),
                source="benchmark",
                ingested_at=now - timedelta(days=d),
                quality_status="FRESH",
                is_daily_bar=True,
            ))

        current_price = Decimal("107.80")
        snap = MarketSnapshot(
            symbol_id=sym.id,
            price=current_price,
            volume=3_200_000,
            previous_close=Decimal("100.00"),
            open=Decimal("100.00"),
            high=Decimal("108.00"),
            low=Decimal("99.50"),
            source="benchmark",
            ingested_at=now,
            quality_status="FRESH",
        )
        db.add(snap)
        await db.flush()

        explanation = template_explanation(
            symbol=sym.symbol, attention_level="HIGH", stock_pct_change=7.8,
            bench_pct_change=0.5, volume_ratio=3.2, news_count_24h=2, breakout=0.3,
        )
        source = "template"

        event = MarketEvent(
            symbol_id=sym.id,
            snapshot_id=snap.id,
            event_type="COMPOSITE",
            magnitude=Decimal("7.80"),
            signals={
                "price_move": 0.9, "volume_spike": 0.75, "relative_move": 0.4,
                "breakout": 0.3, "news_surge": 0.3, "corroboration_boost": 0.1,
                "raw_score": 0.55, "final_score": 0.6, "confidence": 0.85,
                "attention_level": "HIGH", "stock_pct_change": 7.8,
                "bench_pct_change": 0.5, "transition": "NEW",
                "volume_ratio": 3.2, "explanation": explanation,
                "explanation_source": source,
            },
        )
        db.add(event)

        # Baseline from "yesterday" so every event is visible as pending.
        db.add(UserObservation(
            user_id=user.id,
            symbol_id=sym.id,
            last_observed_at=now - timedelta(days=1),
            last_observed_snapshot_id=None,
        ))

    await db.commit()
    return user.id, wl.id, symbol_ids


async def _cleanup(db, user_id: str, symbol_ids: list[str]) -> None:
    await db.execute(delete(Symbol).where(Symbol.id.in_(symbol_ids)))  # cascades
    await db.execute(delete(User).where(User.id == user_id))  # cascades
    await db.commit()


async def run() -> None:
    print(f"{'Symbols':>8} | {'min (ms)':>10} | {'avg (ms)':>10} | {'max (ms)':>10} | items")
    print("-" * 60)

    for n in WATCHLIST_SIZES:
        async with AsyncSessionLocal() as db:
            user_id, wl_id, symbol_ids = await _seed(db, n)

        try:
            # Warm-up call, excluded from timing: SQLAlchemy compiles and
            # caches each distinct query shape the first time it runs in
            # the process, and asyncpg caches prepared statements per
            # connection — a one-time cost with nothing to do with the
            # actual code path, but it otherwise dominates whichever
            # watchlist size happens to run first.
            async with AsyncSessionLocal() as db:
                await attention_service.get_changes(db, wl_id, user_id)

            timings = []
            items_seen = 0
            for _ in range(ITERATIONS_PER_SIZE):
                async with AsyncSessionLocal() as db:
                    t0 = time.perf_counter()
                    result = await attention_service.get_changes(db, wl_id, user_id)
                    elapsed_ms = (time.perf_counter() - t0) * 1000
                    timings.append(elapsed_ms)
                    items_seen = len(result.items)

            print(f"{n:>8} | {min(timings):>10.1f} | {sum(timings)/len(timings):>10.1f} | {max(timings):>10.1f} | {items_seen}")
        finally:
            async with AsyncSessionLocal() as db:
                await _cleanup(db, user_id, symbol_ids)

    print("\nAll runs seed real DB rows and call attention_service.get_changes()")
    print("directly — no Finnhub/yfinance/Gemini calls happen during seeding or")
    print("during the timed reads (explanations are pre-generated with the pure")
    print("template_explanation() function). This is the number that matters:")
    print("it's what a user's dashboard load actually waits on.")


if __name__ == "__main__":
    asyncio.run(run())
