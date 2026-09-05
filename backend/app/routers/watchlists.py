"""
Watchlist + Stock routers.
"""
import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import (
    AddSymbolRequest,
    CandlesResponse,
    ProviderConflictOut,
    SymbolOut,
    SymbolSearchResult,
    WatchlistCreate,
    WatchlistItemOut,
    WatchlistOut,
)
from app.services import watchlist_service

router = APIRouter(prefix="/api/watchlists", tags=["watchlists"])
stock_router = APIRouter(prefix="/api/stocks", tags=["stocks"])


# ── Watchlist CRUD ────────────────────────────────────────────────────────────

@router.get("", response_model=list[WatchlistOut])
async def list_watchlists(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return await watchlist_service.get_user_watchlists(db, current_user.id)


@router.post("", response_model=WatchlistOut, status_code=status.HTTP_201_CREATED)
async def create_watchlist(
    payload: WatchlistCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await watchlist_service.create_watchlist(db, current_user.id, payload)


@router.get("/{watchlist_id}", response_model=WatchlistOut)
async def get_watchlist(
    watchlist_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wl = await watchlist_service.get_watchlist(db, watchlist_id, current_user.id)
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return wl


@router.delete("/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watchlist(
    watchlist_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = await watchlist_service.delete_watchlist(db, watchlist_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Watchlist not found")


# ── Symbol management ─────────────────────────────────────────────────────────

@router.post(
    "/{watchlist_id}/symbols",
    response_model=WatchlistItemOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_symbol(
    watchlist_id: str,
    payload: AddSymbolRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item, provider_conflict = await watchlist_service.add_symbol_to_watchlist(
        db, watchlist_id, current_user.id, payload.symbol
    )
    if not item:
        raise HTTPException(
            status_code=404,
            detail=f"Symbol '{payload.symbol}' not found or watchlist does not exist",
        )

    # Fire-and-forget: backfill 30 days of real candles so charts aren't empty
    # while waiting for the poll scheduler to accumulate history naturally.
    from app.services.ingestion_service import bootstrap_historical
    asyncio.create_task(bootstrap_historical(item.symbol.id, item.symbol.symbol))

    # Explicitly constructed (not just `return item`): provider_conflict is
    # ephemeral, produced only by this request's resolution flow, and isn't
    # an attribute on the WatchlistItem ORM object — FastAPI's automatic
    # response_model serialization has nothing to pull it from otherwise.
    return WatchlistItemOut(
        id=item.id,
        symbol=SymbolOut.model_validate(item.symbol),
        added_at=item.added_at,
        provider_conflict=ProviderConflictOut(**provider_conflict) if provider_conflict else None,
    )


@router.delete("/{watchlist_id}/symbols/{symbol_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_symbol(
    watchlist_id: str,
    symbol_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    removed = await watchlist_service.remove_symbol_from_watchlist(
        db, watchlist_id, current_user.id, symbol_id
    )
    if not removed:
        raise HTTPException(status_code=404, detail="Symbol or watchlist not found")


# ── Stock search ──────────────────────────────────────────────────────────────

@stock_router.get("/search", response_model=list[SymbolSearchResult])
async def search_stocks(q: str = "", db: AsyncSession = Depends(get_db)):
    if len(q) < 1:
        return []
    symbols = await watchlist_service.search_symbols(db, q)
    return [
        SymbolSearchResult(
            symbol=s.symbol,
            company_name=s.company_name,
            sector=s.sector,
            exchange=s.exchange,
        )
        for s in symbols
    ]


# ── Candles (for real-time charts) ─────────────────────────────────────────────

_RANGE_TO_DAYS = {"1D": 1, "1W": 7, "1M": 30}


@stock_router.get("/{symbol}/candles", response_model=CandlesResponse)
async def get_candles(symbol: str, range: str = "1W", db: AsyncSession = Depends(get_db)):
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from app.models import MarketSnapshot, Symbol
    from app.schemas import CandlePoint

    days = _RANGE_TO_DAYS.get(range.upper(), 7)
    range_key = range.upper() if range.upper() in _RANGE_TO_DAYS else "1W"

    sym_result = await db.execute(select(Symbol).where(Symbol.symbol == symbol.upper()))
    sym = sym_result.scalar_one_or_none()
    if not sym:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")

    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    snap_result = await db.execute(
        select(MarketSnapshot)
        .where(MarketSnapshot.symbol_id == sym.id, MarketSnapshot.ingested_at >= cutoff)
        .order_by(MarketSnapshot.ingested_at.asc())
    )
    snapshots = list(snap_result.scalars().all())

    return CandlesResponse(
        symbol=sym.symbol,
        range=range_key,
        points=[
            CandlePoint(timestamp=s.ingested_at, price=s.price, volume=s.volume)
            for s in snapshots
        ],
    )
