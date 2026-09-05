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
    UserObservation,
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
    # Scoped to the user's primary (first-created) watchlist — the only one
    # the UI actually surfaces (see README's Known Limitations: multiple
    # watchlists are supported by the schema but deliberately not exposed).
    # This used to aggregate across every watchlist the user owns, which
    # silently diverges the moment a user has more than one — as this dev
    # database demonstrated: a seed-script idempotency bug (fixed alongside
    # this) had left 6 duplicate "My Watchlist" rows for the demo account,
    # each independently holding the same symbols, so summing across all of
    # them inflated the header's attention counts to 4-5x what /changes
    # (correctly scoped to just the one visible watchlist) actually showed.
    user_watchlists = await watchlist_service.get_user_watchlists(db, current_user.id)
    primary_wl = user_watchlists[0] if user_watchlists else None
    symbol_ids = [item.symbol_id for item in primary_wl.items] if primary_wl else []

    total_symbols = len(symbol_ids)

    from datetime import timedelta
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=24)
    symbols_with_events = 0
    if symbol_ids:
        evented_result = await db.execute(
            select(func.count(func.distinct(MarketEvent.symbol_id)))
            .where(MarketEvent.detected_at >= cutoff, MarketEvent.symbol_id.in_(symbol_ids))
        )
        symbols_with_events = evented_result.scalar() or 0

    # Attention level counts — MUST reflect the same "still pending since
    # your baseline" semantics as /changes, not a blind rolling time window.
    # A naive `UserAttention.computed_at >= cutoff` count (the previous
    # approach) keeps counting an item as CRITICAL for a full 24h after its
    # explanation was first generated, even after the user has committed
    # their observation past that event — producing a header badge that
    # visibly contradicts "all caught up" right below it. Deriving from the
    # actual get_changes() output guarantees the two can never disagree,
    # because they're counting the same thing.
    critical_count = high_count = watch_count = 0
    if primary_wl:
        changes = await attention_service.get_changes(db, primary_wl.id, current_user.id)
        for item in changes.items:
            if item.attention_level == "CRITICAL":
                critical_count += 1
            elif item.attention_level == "HIGH":
                high_count += 1
            elif item.attention_level == "WATCH":
                watch_count += 1

    # Last poll time (system-wide data-freshness fact, not user-specific)
    last_snap = await db.execute(
        select(func.max(MarketSnapshot.ingested_at))
    )
    last_poll = last_snap.scalar()

    # Last time this user actually looked at their (primary) watchlist
    last_checked = None
    if symbol_ids:
        last_checked_result = await db.execute(
            select(func.max(UserObservation.last_observed_at)).where(
                UserObservation.user_id == current_user.id,
                UserObservation.symbol_id.in_(symbol_ids),
            )
        )
        last_checked = last_checked_result.scalar()

    us_open = is_market_open()
    ind_open = is_indian_market_open()

    return DashboardSummary(
        total_symbols_tracked=total_symbols,
        symbols_with_events=symbols_with_events,
        critical_count=critical_count,
        high_count=high_count,
        watch_count=watch_count,
        last_poll_at=last_poll,
        last_checked_at=last_checked,
        market_open=us_open or ind_open,
        us_market_open=us_open,
        indian_market_open=ind_open,
    )


# ── Admin: manual trigger ─────────────────────────────────────────────────────
# Unauthenticated + unthrottled, this endpoint lets anyone on the internet
# force real calls against the shared Finnhub free-tier quota. Auth turns
# "anyone" into "a real account"; the cooldown stops even a real account
# from hammering it (this is also the frontend's "Refresh" button).

_last_trigger_at: datetime | None = None
_TRIGGER_COOLDOWN_SECONDS = 30


@router.post("/admin/trigger-poll")
async def trigger_poll(current_user: User = Depends(get_current_user)):
    """Manually trigger a market data poll (for demos)."""
    global _last_trigger_at
    import asyncio

    now = datetime.now(tz=timezone.utc)
    if _last_trigger_at and (now - _last_trigger_at).total_seconds() < _TRIGGER_COOLDOWN_SECONDS:
        raise HTTPException(
            status_code=429,
            detail="Poll was triggered recently — try again in a few seconds.",
        )
    _last_trigger_at = now

    from app.services.ingestion_service import poll_market_data, poll_news
    asyncio.create_task(poll_market_data())
    asyncio.create_task(poll_news())
    return {"status": "poll triggered"}


@router.post("/admin/demo-scenario")
async def demo_scenario(
    watchlist_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Seeds a deterministic "you were away for 4h12m" scenario through the
    real ingestion -> change-detection -> scoring pipeline, for reliable
    live demos that don't depend on the market doing something interesting
    at the right moment (or on any external API being reachable at all).
    """
    wl = await watchlist_service.get_watchlist(db, watchlist_id, current_user.id)
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    from app.services.demo_service import run_demo_scenario
    result = await run_demo_scenario(db, current_user.id, watchlist_id)
    return result
