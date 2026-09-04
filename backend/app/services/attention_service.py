"""
Attention service — the core "what changed since you last looked?" engine.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    MarketEvent,
    MarketSnapshot,
    NewsEvent,
    Symbol,
    UserObservation,
    Watchlist,
    WatchlistItem,
)
from app.schemas import AttentionItem, ChangesResponse, NewsEventOut, SignalBreakdown
from app.services.explanation_service import get_or_generate_explanation
from app.services.ingestion_service import _get_avg_volume, _count_news_24h

logger = logging.getLogger(__name__)


async def get_changes(
    db: AsyncSession, watchlist_id: str, user_id: str
) -> ChangesResponse:
    """
    Main attention pipeline:
    1. Get all symbols in watchlist + their observation baselines
    2. Fetch events since last observation
    3. Score + explain
    4. Rank by score DESC, filter NO_CHANGE
    """
    # Verify watchlist ownership
    wl_result = await db.execute(
        select(Watchlist)
        .where(Watchlist.id == watchlist_id, Watchlist.user_id == user_id)
        .options(selectinload(Watchlist.items).selectinload(WatchlistItem.symbol))
    )
    wl = wl_result.scalar_one_or_none()
    if not wl:
        return ChangesResponse(
            watchlist_id=watchlist_id,
            user_id=user_id,
            items=[],
            all_caught_up=True,
            generated_at=datetime.now(tz=timezone.utc),
        )

    items: list[AttentionItem] = []

    for wl_item in wl.items:
        symbol = wl_item.symbol

        # Get user baseline
        obs_result = await db.execute(
            select(UserObservation).where(
                UserObservation.user_id == user_id,
                UserObservation.symbol_id == symbol.id,
            )
        )
        obs = obs_result.scalar_one_or_none()
        baseline_at = obs.last_observed_at if obs else (
            datetime.now(tz=timezone.utc) - timedelta(days=1)
        )

        # Get events since baseline
        events_result = await db.execute(
            select(MarketEvent)
            .where(
                MarketEvent.symbol_id == symbol.id,
                MarketEvent.detected_at > baseline_at,
            )
            .order_by(MarketEvent.detected_at.desc())
        )
        events = list(events_result.scalars().all())

        if not events:
            continue

        # Use highest-scored event for this symbol
        best_event = max(events, key=lambda e: float(e.signals.get("final_score", 0)))

        avg_vol = await _get_avg_volume(db, symbol.id)
        news_24h = await _count_news_24h(db, symbol.id)

        ua = await get_or_generate_explanation(
            db=db,
            event=best_event,
            symbol=symbol,
            user_id=user_id,
            avg_volume=avg_vol,
            news_count_24h=news_24h,
        )
        await db.commit()

        if ua.attention_level == "NO_CHANGE":
            continue

        # Get latest snapshot
        snap_result = await db.execute(
            select(MarketSnapshot)
            .where(MarketSnapshot.symbol_id == symbol.id)
            .order_by(MarketSnapshot.ingested_at.desc())
            .limit(1)
        )
        snap = snap_result.scalar_one_or_none()

        # Get recent news (last 3)
        news_result = await db.execute(
            select(NewsEvent)
            .where(NewsEvent.symbol_id == symbol.id)
            .order_by(NewsEvent.published_at.desc())
            .limit(3)
        )
        recent_news = list(news_result.scalars().all())

        sigs = best_event.signals
        stock_pct = float(sigs.get("stock_pct_change", 0))
        freshness = snap.quality_status if snap else "STALE"

        items.append(
            AttentionItem(
                symbol=symbol.symbol,
                company_name=symbol.company_name,
                sector=symbol.sector,
                attention_level=ua.attention_level,
                score=float(ua.score),
                confidence=float(ua.confidence),
                explanation=ua.explanation or "",
                explanation_source=ua.explanation_source,
                event_type=best_event.event_type,
                magnitude=float(best_event.magnitude) if best_event.magnitude else None,
                current_price=snap.price if snap else None,
                price_change_pct=round(stock_pct, 4),
                volume=snap.volume if snap else None,
                latest_news=[
                    NewsEventOut(
                        id=n.id,
                        headline=n.headline,
                        summary=n.summary,
                        source=n.source,
                        url=n.url,
                        published_at=n.published_at,
                    )
                    for n in recent_news
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

    # Sort by score DESC
    items.sort(key=lambda x: x.score, reverse=True)

    return ChangesResponse(
        watchlist_id=watchlist_id,
        user_id=user_id,
        items=items,
        all_caught_up=len(items) == 0,
        generated_at=datetime.now(tz=timezone.utc),
    )
