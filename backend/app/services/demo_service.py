"""
Deterministic demo/replay scenario — "you were away for 4h12m".

Goes through the SAME pipeline as real data (snapshot -> change detection
-> scoring -> event) rather than faking UI data. The only thing that's
synthetic is the input: no external provider calls are made, so this works
fully offline and produces the same result every time — a live 5-minute
demo window shouldn't have to hope Finnhub happens to have something
interesting happen.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MarketEvent, MarketSnapshot, NewsEvent, Symbol, UserObservation, WatchlistItem
from app.services.ingestion_service import run_change_detection

_AWAY_FOR = timedelta(hours=4, minutes=12)

# symbol -> (baseline_price, current_price, baseline_volume, current_volume)
_SCENARIO: dict[str, tuple[float, float, int, int]] = {
    "NVDA": (170.00, 183.26, 42_000_000, 134_400_000),  # +7.8%, 3.2x volume
    "TSLA": (340.00, 329.46, 58_000_000, 104_400_000),  # -3.1%, 1.8x volume
    "MSFT": (510.00, 522.24, 21_000_000, 27_300_000),   # +2.4%
    "AAPL": (240.00, 240.86, 45_000_000, 46_800_000),   # +0.4% — quiet, contrast
    "AMZN": (220.00, 219.10, 33_000_000, 33_900_000),   # -0.4% — quiet, contrast
}


def _daily_bar_hash(symbol: str, day: str) -> str:
    return hashlib.sha256(f"demo|{symbol}|{day}".encode()).hexdigest()[:64]


async def run_demo_scenario(db: AsyncSession, user_id: str, watchlist_id: str) -> dict:
    """Seeds the scenario for the 5 symbols above (adding any that aren't
    already in the watchlist), then runs the real change-detection pipeline
    so the resulting attention items are genuinely computed, not pre-baked."""
    now = datetime.now(tz=timezone.utc)
    baseline_at = now - _AWAY_FOR

    symbols_by_ticker: dict[str, Symbol] = {}
    result = await db.execute(select(Symbol).where(Symbol.symbol.in_(_SCENARIO.keys())))
    for sym in result.scalars().all():
        symbols_by_ticker[sym.symbol] = sym

    processed: list[str] = []

    for ticker, (baseline_price, current_price, baseline_vol, current_vol) in _SCENARIO.items():
        symbol = symbols_by_ticker.get(ticker)
        if not symbol:
            continue  # not seeded — skip rather than invent a catalog entry

        # Ensure it's actually in the target watchlist.
        existing_item = await db.execute(
            select(WatchlistItem).where(
                WatchlistItem.watchlist_id == watchlist_id,
                WatchlistItem.symbol_id == symbol.id,
            )
        )
        if not existing_item.scalar_one_or_none():
            # is_demo=True only here — a symbol the user already tracked
            # keeps is_demo=False even though the demo also touches its
            # snapshot/event data, so real holdings are never auto-removed.
            db.add(WatchlistItem(watchlist_id=watchlist_id, symbol_id=symbol.id, is_demo=True))
            await db.flush()

        # 30 days of consistent daily-bar history so volume/breakout signals
        # are real, not zero — tagged is_daily_bar so the volume baseline
        # (ingestion_service._select_volume_baseline) uses them correctly.
        for i in range(30, 0, -1):
            day = now - timedelta(days=i)
            # Gentle deterministic drift toward the baseline price — not
            # random, so the scenario is bit-for-bit reproducible.
            drift = baseline_price * (1 + 0.002 * (30 - i) / 30 * (1 if i % 2 == 0 else -1))
            db.add(MarketSnapshot(
                symbol_id=symbol.id,
                price=Decimal(str(round(drift, 2))),
                volume=baseline_vol,
                previous_close=Decimal(str(round(drift, 2))),
                open=Decimal(str(round(drift, 2))),
                high=Decimal(str(round(drift * 1.01, 2))),
                low=Decimal(str(round(drift * 0.99, 2))),
                source="demo",
                provider_timestamp=day,
                ingested_at=day,
                quality_status="FRESH",
                is_daily_bar=True,
            ))

        # The baseline snapshot — "what you saw when you last checked".
        baseline_snap = MarketSnapshot(
            symbol_id=symbol.id,
            price=Decimal(str(baseline_price)),
            volume=baseline_vol,
            previous_close=Decimal(str(baseline_price)),
            open=Decimal(str(baseline_price)),
            high=Decimal(str(baseline_price)),
            low=Decimal(str(baseline_price)),
            source="demo",
            provider_timestamp=baseline_at,
            ingested_at=baseline_at,
            quality_status="FRESH",
        )
        db.add(baseline_snap)
        await db.flush()

        # Point the user's observation baseline at it, as if they genuinely
        # checked 4h12m ago.
        obs_result = await db.execute(
            select(UserObservation).where(
                UserObservation.user_id == user_id,
                UserObservation.symbol_id == symbol.id,
            )
        )
        obs = obs_result.scalar_one_or_none()
        if obs:
            obs.last_observed_at = baseline_at
            obs.last_observed_snapshot_id = baseline_snap.id
        else:
            db.add(UserObservation(
                user_id=user_id,
                symbol_id=symbol.id,
                last_observed_at=baseline_at,
                last_observed_snapshot_id=baseline_snap.id,
            ))

        # The "current" snapshot — the dramatic move — inserted as if a
        # live poll had just landed. previous_close is the same baseline
        # price, so "today's move" and "since you checked" agree here
        # (this scenario has no separate intraday history before baseline).
        current_snap = MarketSnapshot(
            symbol_id=symbol.id,
            price=Decimal(str(current_price)),
            volume=current_vol,
            previous_close=Decimal(str(baseline_price)),
            open=Decimal(str(baseline_price)),
            high=Decimal(str(max(baseline_price, current_price) * 1.005)),
            low=Decimal(str(min(baseline_price, current_price) * 0.995)),
            source="demo",
            provider_timestamp=now,
            ingested_at=now,
            quality_status="FRESH",
        )
        db.add(current_snap)
        await db.flush()

        # The event-dedup logic (correctly) suppresses a "new" event that
        # scores the same as the most recent one for that symbol — which
        # means leftover events from earlier real testing of these same
        # seeded symbols could silently swallow the demo's own events. The
        # demo's entire point is to be reliable regardless of whatever else
        # has happened in this database, so it clears its own target
        # symbols' event history first rather than being at the mercy of
        # dedup logic designed for continuous real polling, not one-off
        # resets.
        await db.execute(delete(MarketEvent).where(MarketEvent.symbol_id == symbol.id))

        if ticker == "NVDA":
            headline = "NVIDIA data center revenue beats estimates on AI demand"
            dedup = _daily_bar_hash(ticker, now.date().isoformat())
            existing_news = await db.execute(select(NewsEvent.id).where(NewsEvent.dedup_hash == dedup))
            if not existing_news.scalar_one_or_none():
                db.add(NewsEvent(
                    symbol_id=symbol.id,
                    headline=headline,
                    summary="Stronger-than-expected data center segment revenue guidance.",
                    source="Demo Wire",
                    url=None,
                    published_at=now - timedelta(hours=1),
                    dedup_hash=dedup,
                ))

        # Run the REAL scoring/event pipeline on this snapshot.
        await run_change_detection(db, symbol, current_snap)
        processed.append(ticker)

    await db.commit()
    return {"scenario": "you_were_away", "away_for_minutes": int(_AWAY_FOR.total_seconds() // 60), "symbols": processed}
