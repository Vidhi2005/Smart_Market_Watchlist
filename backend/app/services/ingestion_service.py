"""
Market data ingestion service — fetches quotes, stores snapshots,
bootstraps historical candles, and runs change detection.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.engine import signals as sig
from app.engine.scoring import RawSignals, classify_transition, score, should_create_event
from app.models import MarketEvent, MarketSnapshot, Symbol, UserObservation
from app.providers.base import MarketDataProvider, QuoteData
from app.providers.alpha_vantage_provider import AlphaVantageProvider
from app.providers.finnhub_provider import FinnhubProvider
from app.providers.twelve_data_provider import TwelveDataProvider
from app.providers.yfinance_provider import YFinanceProvider
from app.services.explanation_service import generate_event_explanation

logger = logging.getLogger(__name__)

# Lightweight in-process operational counters, exposed via /api/health.
# Deliberately not a metrics platform — just enough to answer "is ingestion
# actually working" without grepping logs.
ingestion_stats = {
    "last_poll_started_at": None,
    "last_poll_completed_at": None,
    "last_poll_duration_seconds": None,
    "last_poll_symbols_processed": 0,
    "last_poll_provider_failures": 0,
    "last_poll_fallback_used": 0,
    # Per-provider failure counts, keyed by provider name (only providers
    # actually configured in a chain ever appear here) — e.g.
    # {"finnhub": 2, "twelve_data": 0}. Lets /api/health show which
    # specific provider is having trouble, not just an aggregate count.
    "provider_failures": {},
    "llm_calls_total": 0,
    "llm_fallback_total": 0,
}

# ── Provider routing ──────────────────────────────────────────────────────────
# .NS = NSE (National Stock Exchange of India)
# .BO = BSE (Bombay Stock Exchange)
_INDIAN_SUFFIXES = (".NS", ".BO")

# Lazily-constructed, cached by name — a provider whose API key isn't
# configured resolves to None once and stays that way (no key won't
# suddenly appear at runtime), so it's simply never tried again.
_provider_instances: dict[str, MarketDataProvider | None] = {}

# Small in-process circuit breaker, keyed by provider name (same convention
# as ingestion_stats["provider_failures"]) — not a full circuit-breaker
# library, just enough to stop re-burning ~7s of Finnhub retry/backoff per
# symbol, every single 45s poll cycle, during a sustained rate-limit
# condition. A provider that hits 3 consecutive failures is skipped for 60s;
# a single success resets its counter.
_provider_cooldown_until: dict[str, datetime] = {}
_consecutive_failures: dict[str, int] = defaultdict(int)
_CONSECUTIVE_FAILURE_THRESHOLD = 3
_PROVIDER_COOLDOWN_SECONDS = 60


def _get_named_provider(name: str) -> MarketDataProvider | None:
    if name in _provider_instances:
        return _provider_instances[name]

    provider: MarketDataProvider | None
    if name == "finnhub":
        provider = FinnhubProvider(settings.finnhub_api_key) if settings.finnhub_api_key else None
    elif name == "yfinance":
        provider = YFinanceProvider()  # no key needed, always available
    elif name == "alpha_vantage":
        provider = AlphaVantageProvider(settings.alpha_vantage_api_key) if settings.alpha_vantage_api_key else None
    elif name == "twelve_data":
        provider = TwelveDataProvider(settings.twelve_data_api_key) if settings.twelve_data_api_key else None
    else:
        logger.error("Unknown provider name %r in a configured chain — check settings", name)
        provider = None

    _provider_instances[name] = provider
    return provider


def _chain_for(symbol: str) -> list[tuple[str, MarketDataProvider]]:
    """Ordered (name, provider) pairs configured for this symbol's market,
    skipping any entry whose provider isn't available (unknown name, or a
    key-requiring provider with no key configured). Having a key set does
    NOT imply a provider is in the chain — only actually listing it in
    `us_provider_chain`/`india_provider_chain` does."""
    raw = settings.india_provider_chain if symbol.upper().endswith(_INDIAN_SUFFIXES) else settings.us_provider_chain
    names = [n.strip() for n in raw.split(",") if n.strip()]
    chain: list[tuple[str, MarketDataProvider]] = []
    for name in names:
        provider = _get_named_provider(name)
        if provider is not None:
            chain.append((name, provider))
    return chain


def get_provider(symbol: str = "") -> MarketDataProvider:
    """The primary (first-in-chain) provider for this symbol's market —
    used by call sites that only need one provider (company-name lookup,
    news, historical bootstrap), not the full fallback chain."""
    chain = _chain_for(symbol)
    if chain:
        return chain[0][1]
    # Sane configs always resolve at least one provider (yfinance needs no
    # key), but never return None from a function typed to return one.
    return _get_named_provider("yfinance")  # type: ignore[return-value]


async def get_quote_with_fallback_chain(symbol: str) -> tuple[QuoteData | None, list[str]]:
    """
    Tries each provider configured for this symbol's market, in order,
    stopping at the first success. Returns (quote, names_tried) — the
    list always contains every provider actually attempted, so a caller
    can tell not just success/failure but which provider supplied the
    data, or that the whole chain was exhausted.
    """
    tried: list[str] = []
    now = datetime.now(tz=timezone.utc)
    for name, provider in _chain_for(symbol):
        cooldown = _provider_cooldown_until.get(name)
        if cooldown and now < cooldown:
            logger.debug("%s in cooldown until %s — skipping for %s", name, cooldown, symbol)
            continue
        tried.append(name)
        quote = await provider.get_quote(symbol)
        if quote:
            _consecutive_failures[name] = 0
            return quote, tried
        _consecutive_failures[name] += 1
        if _consecutive_failures[name] >= _CONSECUTIVE_FAILURE_THRESHOLD:
            _provider_cooldown_until[name] = now + timedelta(seconds=_PROVIDER_COOLDOWN_SECONDS)
            logger.warning(
                "%s hit %d consecutive failures — cooling down %ds",
                name, _consecutive_failures[name], _PROVIDER_COOLDOWN_SECONDS,
            )
        logger.warning("%s failed for %s — trying next provider in chain", name, symbol)
    return None, tried


# ── Helpers ───────────────────────────────────────────────────────────────────

def _select_volume_baseline(rows: list[tuple[int, bool]]) -> float:
    """
    Pure selection logic, unit-testable without a DB: prefer real daily-bar
    volumes when there are enough of them to be a meaningful baseline (>=3),
    since only those are actually comparable to a single day's volume.
    Falls back to whatever's available otherwise rather than returning
    nothing, but that fallback may mix live-poll readings that aren't a
    clean daily figure (documented approximation, not silently pretended
    away).
    """
    daily = [v for v, is_daily in rows if is_daily and v]
    if len(daily) >= 3:
        return sum(daily) / len(daily)
    all_vols = [v for v, _ in rows if v]
    return sum(all_vols) / len(all_vols) if all_vols else 0.0


async def _get_avg_volume(db: AsyncSession, symbol_id: str, days: int = 30) -> float:
    """Average daily volume baseline from stored snapshots over the last N days."""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(MarketSnapshot.volume, MarketSnapshot.is_daily_bar)
        .where(
            MarketSnapshot.symbol_id == symbol_id,
            MarketSnapshot.ingested_at >= cutoff,
            MarketSnapshot.volume.isnot(None),
        )
    )
    return _select_volume_baseline(list(result.all()))


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

    # Event dedup: don't mint a new MarketEvent every single poll a symbol
    # stays above threshold — only on a real transition (new/escalation/
    # de-escalation) or a meaningful score move within the same level.
    prev_result = await db.execute(
        select(MarketEvent)
        .where(MarketEvent.symbol_id == symbol.id)
        .order_by(MarketEvent.detected_at.desc())
        .limit(1)
    )
    prev_event = prev_result.scalar_one_or_none()
    prev_level = prev_event.signals.get("attention_level") if prev_event else None
    prev_score = prev_event.signals.get("final_score") if prev_event else None

    if not should_create_event(prev_level, prev_score, result.attention_level, result.final_score):
        logger.debug("%s still %s — no new event (continuing state)", symbol.symbol, result.attention_level)
        return None

    transition = classify_transition(prev_level, prev_score, result.attention_level, result.final_score)

    # Generate the explanation HERE — during background ingestion, once per
    # event — never inside a user's GET /changes request. volume_ratio is
    # the real current/average ratio (we have both numbers on hand), not
    # the crude back-conversion from the normalized 0-1 signal score that
    # the old per-user-lazy path had to use for lack of direct access.
    volume_ratio = (float(snapshot.volume) / avg_vol) if (snapshot.volume and avg_vol > 0) else 1.0
    explanation_text, explanation_source = await generate_event_explanation(
        symbol=symbol.symbol,
        company_name=symbol.company_name,
        attention_level=result.attention_level,
        stock_pct_change=stock_pct,
        bench_pct_change=bench_pct,
        volume_ratio=volume_ratio,
        news_count_24h=news_24h,
        breakout=signals.breakout,
        current_price=float(snapshot.price),
        event_type="COMPOSITE",
    )
    ingestion_stats["llm_calls_total"] += 1
    if explanation_source == "template":
        ingestion_stats["llm_fallback_total"] += 1

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
        "transition":          transition,
        "volume_ratio":        round(volume_ratio, 4),
        "explanation":         explanation_text,
        "explanation_source":  explanation_source,
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
    poll_started = datetime.now(tz=timezone.utc)
    ingestion_stats["last_poll_started_at"] = poll_started
    t0 = time.perf_counter()
    processed = 0
    provider_failures = 0
    fallback_used = 0

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
                quote, tried = await get_quote_with_fallback_chain(symbol.symbol)
                succeeded_name = tried[-1] if (quote and tried) else None
                for name in tried:
                    if name != succeeded_name:
                        ingestion_stats["provider_failures"][name] = (
                            ingestion_stats["provider_failures"].get(name, 0) + 1
                        )
                if len(tried) > 1:
                    logger.info("Used fallback chain for %s: tried %s", symbol.symbol, tried)
                    fallback_used += 1
                if not quote:
                    provider_failures += 1
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
                processed += 1
                logger.debug("Ingested %s @ %s", symbol.symbol, quote.price)

                # Rate-limit courtesy: 1 req/sec
                await asyncio.sleep(1.0)

            except Exception as exc:  # noqa: BLE001
                logger.error("Error polling %s: %s", symbol.symbol, exc)
                provider_failures += 1
                await db.rollback()

    duration = time.perf_counter() - t0
    ingestion_stats["last_poll_completed_at"] = datetime.now(tz=timezone.utc)
    ingestion_stats["last_poll_duration_seconds"] = round(duration, 2)
    ingestion_stats["last_poll_symbols_processed"] = processed
    ingestion_stats["last_poll_provider_failures"] = provider_failures
    ingestion_stats["last_poll_fallback_used"] = fallback_used
    logger.info(
        "Poll complete: %d/%d symbols in %.2fs (%d failures, %d fallback)",
        processed, len(symbols), duration, provider_failures, fallback_used,
    )


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
                is_daily_bar=True,
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
