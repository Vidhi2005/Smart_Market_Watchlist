"""
Dashboard and Observation routers + Changes endpoint.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.engine.market_calendar import is_market_open, is_indian_market_open
from app.models import MarketEvent, MarketSnapshot, Symbol, UserAttention, WatchlistItem
from app.schemas import (
    ChangesResponse,
    CommitObservationsRequest,
    DashboardSummary,
)
from app.services import attention_service, observation_service

router = APIRouter(prefix="/api", tags=["dashboard"])

DEMO_USER_ID = settings.demo_user_id


# ── Changes ───────────────────────────────────────────────────────────────────

@router.get("/watchlists/{watchlist_id}/changes", response_model=ChangesResponse)
async def get_changes(watchlist_id: str, db: AsyncSession = Depends(get_db)):
    return await attention_service.get_changes(db, watchlist_id, DEMO_USER_ID)


# ── Commit observations ───────────────────────────────────────────────────────

@router.post("/observations/commit")
async def commit_observations(
    payload: CommitObservationsRequest, db: AsyncSession = Depends(get_db)
):
    updated = await observation_service.commit_observations(
        db,
        user_id=DEMO_USER_ID,
        watchlist_id=payload.watchlist_id,
        symbol_ids=payload.symbol_ids,
    )
    return {"committed": updated}


# ── Dashboard summary ─────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=DashboardSummary)
async def dashboard(db: AsyncSession = Depends(get_db)):
    # Total tracked symbols
    total_result = await db.execute(
        select(func.count(func.distinct(WatchlistItem.symbol_id)))
    )
    total_symbols = total_result.scalar() or 0

    # Symbols with at least one event in the last 24h
    from datetime import timedelta
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=24)
    evented_result = await db.execute(
        select(func.count(func.distinct(MarketEvent.symbol_id)))
        .where(MarketEvent.detected_at >= cutoff)
    )
    symbols_with_events = evented_result.scalar() or 0

    # Attention level counts
    def count_level(level: str):
        return select(func.count(UserAttention.id)).where(
            UserAttention.attention_level == level,
            UserAttention.computed_at >= cutoff,
        )

    crit_res = await db.execute(count_level("CRITICAL"))
    high_res = await db.execute(count_level("HIGH"))
    watch_res = await db.execute(count_level("WATCH"))

    # Last poll time
    last_snap = await db.execute(
        select(func.max(MarketSnapshot.ingested_at))
    )
    last_poll = last_snap.scalar()

    us_open = is_market_open()
    ind_open = is_indian_market_open()

    return DashboardSummary(
        total_symbols_tracked=total_symbols,
        symbols_with_events=symbols_with_events,
        critical_count=crit_res.scalar() or 0,
        high_count=high_res.scalar() or 0,
        watch_count=watch_res.scalar() or 0,
        last_poll_at=last_poll,
        market_open=us_open or ind_open,
        us_market_open=us_open,
        indian_market_open=ind_open,
    )


# ── Admin: manual trigger ─────────────────────────────────────────────────────

@router.post("/admin/trigger-poll")
async def trigger_poll():
    """Manually trigger a market data poll (for demos)."""
    import asyncio
    from app.services.ingestion_service import poll_market_data, poll_news
    asyncio.create_task(poll_market_data())
    asyncio.create_task(poll_news())
    return {"status": "poll triggered"}
