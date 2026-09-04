"""
Watchlist service — all business logic for watchlist CRUD.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Symbol, Watchlist, WatchlistItem
from app.schemas import WatchlistCreate


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


async def add_symbol_to_watchlist(
    db: AsyncSession, watchlist_id: str, user_id: str, ticker: str
) -> WatchlistItem | None:
    """Add a symbol (by ticker string) to a watchlist. Returns None if not found."""
    wl = await get_watchlist(db, watchlist_id, user_id)
    if not wl:
        return None

    # Resolve symbol
    sym_result = await db.execute(
        select(Symbol).where(Symbol.symbol == ticker.upper())
    )
    sym = sym_result.scalar_one_or_none()
    if not sym:
        return None

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
        return result2.scalar_one_or_none()

    item = WatchlistItem(watchlist_id=watchlist_id, symbol_id=sym.id)
    db.add(item)
    await db.commit()
    await db.refresh(item)

    # Reload with symbol relationship
    result3 = await db.execute(
        select(WatchlistItem)
        .where(WatchlistItem.id == item.id)
        .options(selectinload(WatchlistItem.symbol))
    )
    return result3.scalar_one_or_none()


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
