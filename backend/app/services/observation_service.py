"""
Observation service — manages user_observations (the "baseline" concept).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MarketSnapshot, Symbol, UserObservation, Watchlist, WatchlistItem

logger = logging.getLogger(__name__)


async def get_observation(
    db: AsyncSession, user_id: str, symbol_id: str
) -> UserObservation | None:
    result = await db.execute(
        select(UserObservation).where(
            UserObservation.user_id == user_id,
            UserObservation.symbol_id == symbol_id,
        )
    )
    return result.scalar_one_or_none()


async def initialize_observation(
    db: AsyncSession, user_id: str, symbol_id: str
) -> UserObservation:
    """
    Called when a symbol is first added to a watchlist.
    Sets the baseline to the latest snapshot (or now if no snapshot).
    """
    # Get latest snapshot
    snap_result = await db.execute(
        select(MarketSnapshot)
        .where(MarketSnapshot.symbol_id == symbol_id)
        .order_by(MarketSnapshot.ingested_at.desc())
        .limit(1)
    )
    snap = snap_result.scalar_one_or_none()

    obs = UserObservation(
        user_id=user_id,
        symbol_id=symbol_id,
        last_observed_at=datetime.now(tz=timezone.utc),
        last_observed_snapshot_id=snap.id if snap else None,
    )
    db.add(obs)
    await db.flush()
    return obs


async def commit_observations(
    db: AsyncSession,
    user_id: str,
    watchlist_id: str,
    symbol_ids: list[str] | None = None,
) -> int:
    """
    Update the user's observation baseline for symbols in the given watchlist.
    Returns the number of records updated.

    Batched rather than per-symbol: one query for the symbol list, one
    DISTINCT ON for latest snapshots, one for existing observation rows —
    a fixed handful of queries regardless of watchlist size, and each
    UserObservation upsert is idempotent (safe to call twice with the same
    data, e.g. a retried request after a dropped connection).
    """
    q = select(WatchlistItem.symbol_id).where(WatchlistItem.watchlist_id == watchlist_id)
    if symbol_ids:
        q = q.where(WatchlistItem.symbol_id.in_(symbol_ids))
    result = await db.execute(q)
    sym_ids = [r[0] for r in result.all()]
    if not sym_ids:
        return 0

    latest_snap_result = await db.execute(
        select(MarketSnapshot)
        .where(MarketSnapshot.symbol_id.in_(sym_ids))
        .order_by(MarketSnapshot.symbol_id, MarketSnapshot.ingested_at.desc())
        .distinct(MarketSnapshot.symbol_id)
    )
    latest_snap_by_symbol = {s.symbol_id: s for s in latest_snap_result.scalars().all()}

    existing_result = await db.execute(
        select(UserObservation).where(
            UserObservation.user_id == user_id,
            UserObservation.symbol_id.in_(sym_ids),
        )
    )
    existing_by_symbol = {o.symbol_id: o for o in existing_result.scalars().all()}

    now = datetime.now(tz=timezone.utc)
    updated = 0
    for sid in sym_ids:
        snap = latest_snap_by_symbol.get(sid)
        obs = existing_by_symbol.get(sid)
        if obs:
            obs.last_observed_at = now
            obs.last_observed_snapshot_id = snap.id if snap else None
        else:
            db.add(UserObservation(
                user_id=user_id,
                symbol_id=sid,
                last_observed_at=now,
                last_observed_snapshot_id=snap.id if snap else None,
            ))
        updated += 1

    await db.commit()
    return updated
