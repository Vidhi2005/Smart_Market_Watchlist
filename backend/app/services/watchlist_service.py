"""
Watchlist service — all business logic for watchlist CRUD.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Symbol, Watchlist, WatchlistItem
from app.schemas import WatchlistCreate

logger = logging.getLogger(__name__)

# Two providers disagreeing by more than this on the same instrument is
# treated as a data-quality conflict worth logging, not just normal price
# noise between two slightly-offset reads.
_CONFLICT_TOLERANCE_PCT = 2.0


async def get_user_watchlists(db: AsyncSession, user_id: str) -> list[Watchlist]:
    result = await db.execute(
        select(Watchlist)
        .where(Watchlist.user_id == user_id)
        .options(
            selectinload(Watchlist.items).selectinload(WatchlistItem.symbol)
        )
        .order_by(Watchlist.created_at)
    )
    return list(result.scalars().all())


async def get_watchlist(
    db: AsyncSession, watchlist_id: str, user_id: str
) -> Watchlist | None:
    result = await db.execute(
        select(Watchlist)
        .where(Watchlist.id == watchlist_id, Watchlist.user_id == user_id)
        .options(
            selectinload(Watchlist.items).selectinload(WatchlistItem.symbol)
        )
    )
    return result.scalar_one_or_none()


async def create_watchlist(
    db: AsyncSession, user_id: str, payload: WatchlistCreate
) -> Watchlist:
    wl = Watchlist(user_id=user_id, name=payload.name)
    db.add(wl)
    await db.commit()
    await db.refresh(wl)
    return wl


async def delete_watchlist(db: AsyncSession, watchlist_id: str, user_id: str) -> bool:
    wl = await get_watchlist(db, watchlist_id, user_id)
    if not wl:
        return False
    await db.delete(wl)
    await db.commit()
    return True


def detect_price_conflict(
    canonical_price: float, other_price: float, tolerance_pct: float = _CONFLICT_TOLERANCE_PCT
) -> float | None:
    """
    Pure comparison, no I/O — returns the disagreement percentage when it
    exceeds tolerance, else None. Kept separate from the async resolution
    flow so it's directly unit-testable without a DB or network call.
    """
    if canonical_price <= 0:
        return None
    diff_pct = abs(canonical_price - other_price) / canonical_price * 100
    return diff_pct if diff_pct > tolerance_pct else None


async def _check_provider_conflicts(ticker: str, canonical_quote) -> dict | None:
    """
    Cross-checks the canonical quote (the one that resolved the symbol)
    against every OTHER provider configured for this ticker's market —
    still a one-time, symbol-add-time check, not continuous (doubling
    per-poll API calls against free-tier ceilings for marginal benefit
    is the wrong tradeoff regardless of how many providers exist).
    Compares against a single canonical reference rather than every pair,
    since that's what a user-facing message actually needs to say ("X
    disagrees with the value we used"), not a full disagreement matrix.
    """
    from app.services.ingestion_service import _chain_for

    canonical_price = float(canonical_quote.price)
    outliers: list[dict] = []
    checked = 1  # the canonical provider itself counts as checked

    for name, provider in _chain_for(ticker):
        if name == canonical_quote.source:
            continue
        other_quote = await provider.get_quote(ticker)
        if not other_quote:
            continue
        checked += 1
        diff_pct = detect_price_conflict(canonical_price, float(other_quote.price))
        if diff_pct is not None:
            logger.warning(
                "Provider conflict resolving %s: %s=%.2f vs %s=%.2f (%.1f%% apart)",
                ticker, canonical_quote.source, canonical_price, name, float(other_quote.price), diff_pct,
            )
            outliers.append({"provider": name, "price": float(other_quote.price), "diff_pct": round(diff_pct, 2)})

    if not outliers:
        return None
    return {
        "providers_checked": checked,
        "canonical_provider": canonical_quote.source,
        "canonical_price": canonical_price,
        "conflicting": True,
        "outliers": outliers,
    }


async def _resolve_new_symbol(db: AsyncSession, ticker: str) -> tuple[Symbol | None, dict | None]:
    """
    Looks up a ticker that isn't in the local catalog yet via the live
    provider chain instead of only ever offering the ~20 pre-seeded
    symbols. A real quote confirms the ticker exists; the resolved row is
    persisted so future searches (and other users) find it locally
    without another live lookup. Returns (symbol, provider_conflict) —
    the second value is None unless another configured provider's price
    disagreed with the one actually used beyond tolerance.
    """
    from app.services.ingestion_service import get_provider

    provider = get_provider(ticker)
    quote = await provider.get_quote(ticker)
    if not quote:
        return None, None  # not a real/quotable ticker

    conflict = await _check_provider_conflicts(ticker, quote)

    company_name = await provider.get_company_name(ticker)
    exchange = "NSE" if ticker.endswith(".NS") else "BSE" if ticker.endswith(".BO") else None

    sym = Symbol(
        symbol=ticker,
        company_name=company_name or ticker,
        sector=None,
        exchange=exchange,
    )
    db.add(sym)
    await db.commit()
    await db.refresh(sym)
    return sym, conflict


async def add_symbol_to_watchlist(
    db: AsyncSession, watchlist_id: str, user_id: str, ticker: str
) -> tuple[WatchlistItem | None, dict | None]:
    """
    Add a symbol (by ticker string) to a watchlist. Returns
    (item, provider_conflict) — item is None if not found/resolvable.
    provider_conflict is only ever non-None when resolving a brand-new
    ticker triggered a live cross-provider check that disagreed beyond
    tolerance (see `_check_provider_conflicts`); an already-catalogued
    symbol has nothing to report since no new provider call was made.
    """
    wl = await get_watchlist(db, watchlist_id, user_id)
    if not wl:
        return None, None

    ticker = ticker.strip().upper()

    # Resolve symbol — check the local catalog first, then fall back to a
    # live provider lookup for tickers nobody has added yet.
    sym_result = await db.execute(select(Symbol).where(Symbol.symbol == ticker))
    sym = sym_result.scalar_one_or_none()
    conflict: dict | None = None
    if not sym:
        sym, conflict = await _resolve_new_symbol(db, ticker)
    if not sym:
        return None, None

    # Idempotent insert
    existing = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.watchlist_id == watchlist_id,
            WatchlistItem.symbol_id == sym.id,
        )
    )
    if existing.scalar_one_or_none():
        # Already there — just return it
        result2 = await db.execute(
            select(WatchlistItem)
            .where(
                WatchlistItem.watchlist_id == watchlist_id,
                WatchlistItem.symbol_id == sym.id,
            )
            .options(selectinload(WatchlistItem.symbol))
        )
        return result2.scalar_one_or_none(), conflict

    item = WatchlistItem(watchlist_id=watchlist_id, symbol_id=sym.id)
    db.add(item)
    await db.flush()

    # Give the symbol a real baseline immediately instead of leaving it to
    # attention_service's "no observation yet" fallback (previously-dead
    # code — this was defined but never called).
    from app.services.observation_service import initialize_observation
    await initialize_observation(db, user_id, sym.id)

    await db.commit()
    await db.refresh(item)

    # Reload with symbol relationship
    result3 = await db.execute(
        select(WatchlistItem)
        .where(WatchlistItem.id == item.id)
        .options(selectinload(WatchlistItem.symbol))
    )
    return result3.scalar_one_or_none(), conflict


async def remove_symbol_from_watchlist(
    db: AsyncSession, watchlist_id: str, user_id: str, symbol_id: str
) -> bool:
    wl = await get_watchlist(db, watchlist_id, user_id)
    if not wl:
        return False

    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.watchlist_id == watchlist_id,
            WatchlistItem.symbol_id == symbol_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        return False

    await db.delete(item)
    await db.commit()
    return True


async def search_symbols(db: AsyncSession, query: str, limit: int = 10) -> list[Symbol]:
    q = f"%{query.upper()}%"
    result = await db.execute(
        select(Symbol)
        .where(
            (Symbol.symbol.ilike(q)) | (Symbol.company_name.ilike(f"%{query}%"))
        )
        .limit(limit)
        .order_by(Symbol.symbol)
    )
    return list(result.scalars().all())
