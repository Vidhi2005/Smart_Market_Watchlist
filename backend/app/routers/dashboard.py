"""
Dashboard and Observation routers + Changes endpoint.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.engine.market_calendar import is_market_open, is_indian_market_open
from app.models import (
    MarketEvent,
    MarketSnapshot,
    User,
    UserAttention,
    UserObservation,
    Watchlist,
    WatchlistItem,
)
from app.schemas import (
    ChangesResponse,
    CommitObservationsRequest,
    DashboardSummary,
    QuoteOut,
)
from app.services import attention_service, observation_service, watchlist_service

router = APIRouter(prefix="/api", tags=["dashboard"])


# ── Changes ───────────────────────────────────────────────────────────────────

@router.get("/watchlists/{watchlist_id}/changes", response_model=ChangesResponse)
async def get_changes(
    watchlist_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await attention_service.get_changes(db, watchlist_id, current_user.id)


# ── Quotes: live market data for every tracked symbol ──────────────────────────
# Deliberately separate from /changes — "what changed" and "what's the current
# price" are different questions, and the brief asks for both. A quiet stock
# with no attention event still has a real price a user should be able to see.

@router.get("/watchlists/{watchlist_id}/quotes", response_model=list[QuoteOut])
async def get_quotes(
    watchlist_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wl = await watchlist_service.get_watchlist(db, watchlist_id, current_user.id)
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    quotes: list[QuoteOut] = []
    for item in wl.items:
        symbol = item.symbol
        snap_result = await db.execute(
            select(MarketSnapshot)
            .where(MarketSnapshot.symbol_id == symbol.id)
            .order_by(MarketSnapshot.ingested_at.desc())
            .limit(1)
        )
        snap = snap_result.scalar_one_or_none()

        price_change_pct = None
        if snap and snap.previous_close:
            prev = float(snap.previous_close)
            if prev != 0:
                price_change_pct = round((float(snap.price) - prev) / prev * 100, 4)

        quotes.append(
            QuoteOut(
                symbol=symbol.symbol,
                company_name=symbol.company_name,
                sector=symbol.sector,
                exchange=symbol.exchange,
                current_price=snap.price if snap else None,
                price_change_pct=price_change_pct,
                volume=snap.volume if snap else None,
                data_freshness=snap.quality_status if snap else "NO_DATA",
            )
        )

    return quotes


# ── Commit observations ───────────────────────────────────────────────────────

@router.post("/observations/commit")
async def commit_observations(
    payload: CommitObservationsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated = await observation_service.commit_observations(
        db,
        user_id=current_user.id,
        watchlist_id=payload.watchlist_id,
        symbol_ids=payload.symbol_ids,
    )
    return {"committed": updated}


# ── Dashboard summary ─────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=DashboardSummary)
async def dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Every count below is scoped to the current user's own watchlist(s) —
    # this endpoint used to run unscoped across the whole DB, which was a
    # cross-user data leak now that multiple real accounts exist.
    user_symbol_ids_subq = (
        select(WatchlistItem.symbol_id)
        .join(Watchlist, Watchlist.id == WatchlistItem.watchlist_id)
        .where(Watchlist.user_id == current_user.id)
        .distinct()
    )

    total_result = await db.execute(
        select(func.count()).select_from(user_symbol_ids_subq.subquery())
    )
    total_symbols = total_result.scalar() or 0

    # Symbols with at least one event in the last 24h
    from datetime import timedelta
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=24)
    evented_result = await db.execute(
        select(func.count(func.distinct(MarketEvent.symbol_id)))
        .where(
            MarketEvent.detected_at >= cutoff,
            MarketEvent.symbol_id.in_(user_symbol_ids_subq),
        )
    )
    symbols_with_events = evented_result.scalar() or 0

    # Attention level counts — scoped to this user's own UserAttention rows
    def count_level(level: str):
        return select(func.count(UserAttention.id)).where(
            UserAttention.user_id == current_user.id,
            UserAttention.attention_level == level,
            UserAttention.computed_at >= cutoff,
        )

    crit_res = await db.execute(count_level("CRITICAL"))
    high_res = await db.execute(count_level("HIGH"))
    watch_res = await db.execute(count_level("WATCH"))

    # Last poll time (system-wide data-freshness fact, not user-specific)
    last_snap = await db.execute(
        select(func.max(MarketSnapshot.ingested_at))
    )
    last_poll = last_snap.scalar()

    # Last time this user actually looked at their watchlist
    last_checked_result = await db.execute(
        select(func.max(UserObservation.last_observed_at)).where(
            UserObservation.user_id == current_user.id
        )
    )
    last_checked = last_checked_result.scalar()

    us_open = is_market_open()
    ind_open = is_indian_market_open()

    return DashboardSummary(
        total_symbols_tracked=total_symbols,
        symbols_with_events=symbols_with_events,
        critical_count=crit_res.scalar() or 0,
        high_count=high_res.scalar() or 0,
        watch_count=watch_res.scalar() or 0,
        last_poll_at=last_poll,
        last_checked_at=last_checked,
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
