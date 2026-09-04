"""
Market data ingestion service — fetches quotes, stores snapshots,
bootstraps historical candles, and runs change detection.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.engine import signals as sig
from app.engine.scoring import RawSignals, score
from app.models import MarketEvent, MarketSnapshot, Symbol, UserObservation
from app.providers.base import MarketDataProvider
from app.providers.finnhub_provider import FinnhubProvider
from app.providers.yfinance_provider import YFinanceProvider

logger = logging.getLogger(__name__)

# ── Provider routing ──────────────────────────────────────────────────────────
# .NS = NSE (National Stock Exchange of India)
# .BO = BSE (Bombay Stock Exchange)
_INDIAN_SUFFIXES = (".NS", ".BO")

_finnhub_provider: FinnhubProvider | None = None
_yfinance_provider: YFinanceProvider | None = None


def get_provider(symbol: str = "") -> MarketDataProvider:
    """Return the right provider for the given ticker symbol.

    - Symbols ending in .NS or .BO  →  YFinanceProvider (free, no key needed)
    - Everything else               →  FinnhubProvider  (US/global markets)
    """
    global _finnhub_provider, _yfinance_provider
    if symbol.upper().endswith(_INDIAN_SUFFIXES):
        if _yfinance_provider is None:
            _yfinance_provider = YFinanceProvider()
        return _yfinance_provider
    else:
        if _finnhub_provider is None:
            _finnhub_provider = FinnhubProvider(settings.finnhub_api_key)
        return _finnhub_provider


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_avg_volume(db: AsyncSession, symbol_id: str, days: int = 30) -> float:
    """Average daily volume from stored snapshots over the last N days."""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(MarketSnapshot.volume)
        .where(
            MarketSnapshot.symbol_id == symbol_id,
            MarketSnapshot.ingested_at >= cutoff,
            MarketSnapshot.volume.isnot(None),
        )
    )
    volumes = [r for r in result.scalars().all() if r]
    return sum(volumes) / len(volumes) if volumes else 0.0


async def _get_price_range_30d(
    db: AsyncSession, symbol_id: str
) -> tuple[Decimal, Decimal]:
    """Returns (high_30d, low_30d) from stored snapshots."""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=30)
    result = await db.execute(
        select(MarketSnapshot.high, MarketSnapshot.low)
        .where(
            MarketSnapshot.symbol_id == symbol_id,
            MarketSnapshot.ingested_at >= cutoff,
            MarketSnapshot.high.isnot(None),
            MarketSnapshot.low.isnot(None),
        )
    )
    rows = result.all()
    if not rows:
        return Decimal("0"), Decimal("0")
    high = max(r[0] for r in rows)
    low = min(r[1] for r in rows)
    return high, low


async def _get_benchmark_pct_change(db: AsyncSession) -> float:
    """Latest SPY pct-change vs previous_close."""
    spy_result = await db.execute(
        select(Symbol).where(Symbol.symbol == settings.benchmark_symbol)
    )
    spy = spy_result.scalar_one_or_none()
    if not spy:
        return 0.0
    snap_result = await db.execute(
        select(MarketSnapshot)
        .where(MarketSnapshot.symbol_id == spy.id)
        .order_by(MarketSnapshot.ingested_at.desc())
        .limit(1)
    )
    snap = snap_result.scalar_one_or_none()
    if not snap or not snap.previous_close:
        return 0.0
    return sig.pct_change(snap.price, snap.previous_close)


# ── News count ────────────────────────────────────────────────────────────────

async def _count_news_24h(db: AsyncSession, symbol_id: str) -> int:
    from app.models import NewsEvent
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=24)
    result = await db.execute(
        select(NewsEvent.id)
        .where(NewsEvent.symbol_id == symbol_id, NewsEvent.published_at >= cutoff)
    )
    return len(result.all())


# ── Change detection ──────────────────────────────────────────────────────────

async def run_change_detection(
    db: AsyncSession, symbol: Symbol, snapshot: MarketSnapshot
) -> MarketEvent | None:
    """Compute signals for a freshly inserted snapshot and maybe create a MarketEvent."""
    if not snapshot.previous_close:
        return None

    avg_vol = await _get_avg_volume(db, symbol.id)
    high_30d, low_30d = await _get_price_range_30d(db, symbol.id)
    bench_pct = await _get_benchmark_pct_change(db)
    news_24h = await _count_news_24h(db, symbol.id)

    stock_pct = sig.pct_change(snapshot.price, snapshot.previous_close)

    signals = RawSignals(
        price_move=sig.price_move_signal(snapshot.price, snapshot.previous_close),
        volume_spike=sig.volume_spike_signal(snapshot.volume or 0, avg_vol),
        relative_move=sig.relative_move_signal(stock_pct, bench_pct),
        breakout=sig.breakout_signal(snapshot.price, high_30d, low_30d) if high_30d > 0 else 0.0,
        news_surge=sig.news_surge_signal(news_24h),
    )

    is_fresh = snapshot.quality_status == "FRESH"
    result = score(signals, data_is_fresh=is_fresh)

    if result.attention_level == "NO_CHANGE":
        return None

    # Build signals JSONB payload
    signals_payload = {
        "price_move":          round(signals.price_move, 4),
        "volume_spike":        round(signals.volume_spike, 4),
        "relative_move":       round(signals.relative_move, 4),
        "breakout":            round(signals.breakout, 4),
        "news_surge":          round(signals.news_surge, 4),
        "corroboration_boost": round(result.corroboration_boost, 4),
        "raw_score":           round(result.raw_score, 4),
        "final_score":         round(result.final_score, 4),
        "confidence":          round(result.confidence, 4),
        "attention_level":     result.attention_level,
        "stock_pct_change":    round(stock_pct, 4),
        "bench_pct_change":    round(bench_pct, 4),
    }

    event = MarketEvent(
        symbol_id=symbol.id,
        snapshot_id=snapshot.id,
        event_type="COMPOSITE",
        magnitude=Decimal(str(round(abs(stock_pct), 4))),
        signals=signals_payload,
    )
    db.add(event)
    await db.flush()
    return event


# ── Main poll function ────────────────────────────────────────────────────────

async def poll_market_data() -> None:
    """Fetch quotes for all tracked symbols and run change detection."""
    # Provider is chosen per-symbol inside the loop; no single provider here

    async with AsyncSessionLocal() as db:
        # Get all unique symbols currently in any watchlist
        from app.models import WatchlistItem
        result = await db.execute(
            select(Symbol)
            .join(WatchlistItem, WatchlistItem.symbol_id == Symbol.id)
            .distinct()
        )
        symbols: list[Symbol] = list(result.scalars().all())

        if not symbols:
            logger.info("No symbols to poll.")
            return

        logger.info("Polling %d symbols…", len(symbols))

        for symbol in symbols:
            try:
                provider = get_provider(symbol.symbol)
                quote = await provider.get_quote(symbol.symbol)
                if not quote:
                    # Mark last snapshot STALE
                    last = await db.execute(
                        select(MarketSnapshot)
                        .where(MarketSnapshot.symbol_id == symbol.id)
                        .order_by(MarketSnapshot.ingested_at.desc())
                        .limit(1)
                    )
                    stale = last.scalar_one_or_none()
                    if stale:
                        stale.quality_status = "STALE"
                        await db.commit()
                    continue

                snapshot = MarketSnapshot(
                    symbol_id=symbol.id,
                    price=quote.price,
                    volume=quote.volume,
                    previous_close=quote.previous_close,
                    open=quote.open,
                    high=quote.high,
                    low=quote.low,
                    source=quote.source,
                    provider_timestamp=quote.provider_timestamp,
                    quality_status="FRESH",
                )
                db.add(snapshot)
                await db.flush()

                await run_change_detection(db, symbol, snapshot)
                await db.commit()
                logger.debug("Ingested %s @ %s", symbol.symbol, quote.price)

                # Rate-limit courtesy: 1 req/sec
                await asyncio.sleep(1.0)

            except Exception as exc:  # noqa: BLE001
                logger.error("Error polling %s: %s", symbol.symbol, exc)
                await db.rollback()


# ── Historical bootstrap ──────────────────────────────────────────────────────

async def bootstrap_historical(symbol_id: str, ticker: str) -> None:
    """
    Called when a symbol is first added. Fetches 30 days of daily candles
    and stores them as FRESH snapshots to populate signal baselines.
    """
    provider = get_provider(ticker)
    to_ts = int(datetime.now(tz=timezone.utc).timestamp())
    from_ts = to_ts - 30 * 86400

    candles = await provider.get_candles(ticker, from_ts, to_ts, resolution="D")
    if not candles:
        logger.warning("No historical candles for %s", ticker)
        return

    async with AsyncSessionLocal() as db:
        for candle in candles:
            snap = MarketSnapshot(
                symbol_id=symbol_id,
                price=candle.close,
                open=candle.open,
                high=candle.high,
                low=candle.low,
                volume=candle.volume,
                previous_close=candle.open,  # approximation for daily candle
                provider_timestamp=candle.timestamp,
                ingested_at=candle.timestamp,
                quality_status="FRESH",
            )
            db.add(snap)
        await db.commit()
        logger.info("Bootstrapped %d daily candles for %s", len(candles), ticker)


# ── News poll ─────────────────────────────────────────────────────────────────

async def poll_news() -> None:
    """Fetch news for all tracked symbols and deduplicate."""
    from app.models import NewsEvent, WatchlistItem

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Symbol)
            .join(WatchlistItem, WatchlistItem.symbol_id == Symbol.id)
            .distinct()
        )
        symbols: list[Symbol] = list(result.scalars().all())

        for symbol in symbols:
            try:
                provider = get_provider(symbol.symbol)
                news_items = await provider.get_news(symbol.symbol, days_back=3)
                new_count = 0
                for item in news_items:
                    h = provider.news_dedup_hash(symbol.symbol, item.headline, item.published_at)
                    # Check existing
                    exists = await db.execute(
                        select(NewsEvent.id).where(NewsEvent.dedup_hash == h)
                    )
                    if exists.scalar_one_or_none():
                        continue
                    ne = NewsEvent(
                        symbol_id=symbol.id,
                        headline=item.headline,
                        summary=item.summary,
                        source=item.source,
                        url=item.url,
                        published_at=item.published_at,
                        dedup_hash=h,
                    )
                    db.add(ne)
                    new_count += 1
                await db.commit()
                if new_count:
                    logger.info("Ingested %d new news items for %s", new_count, symbol.symbol)
                await asyncio.sleep(0.5)
            except Exception as exc:  # noqa: BLE001
                logger.error("Error fetching news for %s: %s", symbol.symbol, exc)
                await db.rollback()
