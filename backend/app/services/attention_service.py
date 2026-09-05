"""
Attention service — the core "what changed since you last looked?" engine.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.signals import pct_change
from app.models import (
    MarketEvent,
    MarketSnapshot,
    NewsEvent,
    UserObservation,
    Watchlist,
    WatchlistItem,
)
from app.schemas import AttentionItem, ChangesResponse, NewsEventOut, SignalBreakdown

logger = logging.getLogger(__name__)

_EVENT_LOOKBACK_DAYS = 30  # matches the signal engine's own 30-day windows
_DEFAULT_BASELINE_LOOKBACK = timedelta(days=1)  # for a symbol never observed


async def get_changes(
    db: AsyncSession, watchlist_id: str, user_id: str
) -> ChangesResponse:
    """
    Main attention pipeline:
    1. Get all symbols in watchlist + their observation baselines (batched)
    2. Fetch events since last observation per symbol (one broad query)
    3. Score + explain (per-item — only real work for actually-flagged items)
    4. Rank by score DESC, filter NO_CHANGE

    Queries are batched across the whole watchlist rather than per-symbol —
    a 50-stock watchlist used to mean ~7N queries; this is a fixed handful
    regardless of N. Pure read: score, confidence, and explanation are all
    read directly off the event's own `signals` JSONB (written once during
    ingestion) — this function never calls an LLM or an external provider.
    """
    t0 = time.perf_counter()
    wl_result = await db.execute(
        select(Watchlist)
        .where(Watchlist.id == watchlist_id, Watchlist.user_id == user_id)
        .options(selectinload(Watchlist.items).selectinload(WatchlistItem.symbol))
    )
    wl = wl_result.scalar_one_or_none()
    if not wl or not wl.items:
        return ChangesResponse(
            watchlist_id=watchlist_id,
            user_id=user_id,
            items=[],
            all_caught_up=True,
            generated_at=datetime.now(tz=timezone.utc),
        )

    symbol_ids = [wi.symbol.id for wi in wl.items]
    now = datetime.now(tz=timezone.utc)
    lookback_cutoff = now - timedelta(days=_EVENT_LOOKBACK_DAYS)

    # ── Batch 1: observation baselines for every symbol at once ────────────
    obs_result = await db.execute(
        select(UserObservation).where(
            UserObservation.user_id == user_id,
            UserObservation.symbol_id.in_(symbol_ids),
        )
    )
    obs_by_symbol = {o.symbol_id: o for o in obs_result.scalars().all()}

    # ── Batch 2: candidate events for every symbol in one bounded query ────
    events_result = await db.execute(
        select(MarketEvent)
        .where(
            MarketEvent.symbol_id.in_(symbol_ids),
            MarketEvent.detected_at >= lookback_cutoff,
        )
        .order_by(MarketEvent.detected_at.desc())
    )
    events_by_symbol: dict[str, list[MarketEvent]] = {}
    for ev in events_result.scalars().all():
        events_by_symbol.setdefault(ev.symbol_id, []).append(ev)

    # ── Batch 3: latest snapshot per symbol (Postgres DISTINCT ON) ─────────
    latest_snap_result = await db.execute(
        select(MarketSnapshot)
        .where(MarketSnapshot.symbol_id.in_(symbol_ids))
        .order_by(MarketSnapshot.symbol_id, MarketSnapshot.ingested_at.desc())
        .distinct(MarketSnapshot.symbol_id)
    )
    latest_snap_by_symbol = {s.symbol_id: s for s in latest_snap_result.scalars().all()}

    # ── Batch 4: 30-day avg volume, grouped ─────────────────────────────────
    avg_vol_by_symbol = await _get_avg_volume_batch(db, symbol_ids)

    # ── Batch 5: news — last 7 days for everyone, grouped in Python ────────
    news_cutoff_7d = now - timedelta(days=7)
    news_result = await db.execute(
        select(NewsEvent)
        .where(NewsEvent.symbol_id.in_(symbol_ids), NewsEvent.published_at >= news_cutoff_7d)
        .order_by(NewsEvent.published_at.desc())
    )
    news_by_symbol: dict[str, list[NewsEvent]] = {}
    for n in news_result.scalars().all():
        news_by_symbol.setdefault(n.symbol_id, []).append(n)

    items: list[AttentionItem] = []

    for wl_item in wl.items:
        symbol = wl_item.symbol
        events = events_by_symbol.get(symbol.id, [])
        if not events:
            continue

        obs = obs_by_symbol.get(symbol.id)
        baseline_at = obs.last_observed_at if obs else (now - _DEFAULT_BASELINE_LOOKBACK)
        events_since_baseline = [e for e in events if e.detected_at > baseline_at]
        if not events_since_baseline:
            continue

        best_event = max(events_since_baseline, key=lambda e: float(e.signals.get("final_score", 0)))
        symbol_news = news_by_symbol.get(symbol.id, [])

        # Pure read — score, confidence, explanation were all computed once
        # during ingestion (see ingestion_service.run_change_detection) and
        # live directly on the event's signals. No LLM call, no write, no
        # per-user duplication: every user watching this symbol reads the
        # exact same event row.
        sigs = best_event.signals
        attention_level = sigs.get("attention_level", "WATCH")
        if attention_level == "NO_CHANGE":
            continue  # defensive — run_change_detection never persists these

        snap = latest_snap_by_symbol.get(symbol.id)
        stock_pct = float(sigs.get("stock_pct_change", 0))
        bench_pct = float(sigs.get("bench_pct_change", 0))
        freshness = snap.quality_status if snap else "STALE"

        # "Since you checked" — the product's actual promise — computed
        # against the user's own baseline snapshot, separate from
        # stock_pct_change (which is vs previous_close, i.e. "today's
        # move"). Only available once the user has a real prior baseline
        # with a price on record.
        since_checked_pct = None
        if obs and obs.last_observed_snapshot_id and snap:
            baseline_snap_result = await db.execute(
                select(MarketSnapshot.price).where(MarketSnapshot.id == obs.last_observed_snapshot_id)
            )
            baseline_price = baseline_snap_result.scalar_one_or_none()
            if baseline_price:
                since_checked_pct = round(pct_change(snap.price, baseline_price), 4)

        items.append(
            AttentionItem(
                symbol=symbol.symbol,
                symbol_id=str(symbol.id),
                company_name=symbol.company_name,
                sector=symbol.sector,
                attention_level=attention_level,
                score=float(sigs.get("final_score", 0)),
                confidence=float(sigs.get("confidence", 1.0)),
                explanation=sigs.get("explanation") or "",
                explanation_source=sigs.get("explanation_source", "template"),
                event_type=best_event.event_type,
                magnitude=float(best_event.magnitude) if best_event.magnitude else None,
                current_price=snap.price if snap else None,
                price_change_pct=round(stock_pct, 4),
                since_checked_change_pct=since_checked_pct,
                volume=snap.volume if snap else None,
                avg_volume_30d=round(avg_vol_by_symbol.get(symbol.id, 0.0), 2) or None,
                benchmark_change_pct=round(bench_pct, 4),
                latest_news=[
                    NewsEventOut(
                        id=n.id,
                        headline=n.headline,
                        summary=n.summary,
                        source=n.source,
                        url=n.url,
                        published_at=n.published_at,
                    )
                    for n in symbol_news[:3]
                ],
                signals=SignalBreakdown(
                    price_move=float(sigs.get("price_move", 0)),
                    volume_spike=float(sigs.get("volume_spike", 0)),
                    relative_move=float(sigs.get("relative_move", 0)),
                    breakout=float(sigs.get("breakout", 0)),
                    news_surge=float(sigs.get("news_surge", 0)),
                    corroboration_boost=float(sigs.get("corroboration_boost", 0)),
                ),
                detected_at=best_event.detected_at,
                data_freshness=freshness,
            )
        )

    items.sort(key=lambda x: x.score, reverse=True)

    elapsed_ms = (time.perf_counter() - t0) * 1000
    logger.debug(
        "get_changes: %d symbols -> %d items in %.1fms (no external calls)",
        len(symbol_ids), len(items), elapsed_ms,
    )

    return ChangesResponse(
        watchlist_id=watchlist_id,
        user_id=user_id,
        items=items,
        all_caught_up=len(items) == 0,
        generated_at=now,
    )


async def _get_avg_volume_batch(db: AsyncSession, symbol_ids: list[str]) -> dict[str, float]:
    """Grouped version of ingestion_service._get_avg_volume for N symbols
    in one query instead of N. Same daily-bar-preferring semantics."""
    from app.services.ingestion_service import _select_volume_baseline

    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=_EVENT_LOOKBACK_DAYS)
    result = await db.execute(
        select(MarketSnapshot.symbol_id, MarketSnapshot.volume, MarketSnapshot.is_daily_bar)
        .where(
            MarketSnapshot.symbol_id.in_(symbol_ids),
            MarketSnapshot.ingested_at >= cutoff,
            MarketSnapshot.volume.isnot(None),
        )
    )
    by_symbol: dict[str, list[tuple[int, bool]]] = {}
    for symbol_id, volume, is_daily_bar in result.all():
        by_symbol.setdefault(symbol_id, []).append((volume, is_daily_bar))

    return {sid: _select_volume_baseline(rows) for sid, rows in by_symbol.items()}
