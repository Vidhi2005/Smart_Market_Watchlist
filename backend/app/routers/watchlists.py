"""
Watchlist + Stock routers.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.schemas import (
    AddSymbolRequest,
    SymbolSearchResult,
    WatchlistCreate,
    WatchlistItemOut,
    WatchlistOut,
)
from app.services import watchlist_service

router = APIRouter(prefix="/api/watchlists", tags=["watchlists"])
stock_router = APIRouter(prefix="/api/stocks", tags=["stocks"])

DEMO_USER_ID = settings.demo_user_id


# ── Watchlist CRUD ────────────────────────────────────────────────────────────

@router.get("", response_model=list[WatchlistOut])
async def list_watchlists(db: AsyncSession = Depends(get_db)):
    return await watchlist_service.get_user_watchlists(db, DEMO_USER_ID)


@router.post("", response_model=WatchlistOut, status_code=status.HTTP_201_CREATED)
async def create_watchlist(
    payload: WatchlistCreate, db: AsyncSession = Depends(get_db)
):
    return await watchlist_service.create_watchlist(db, DEMO_USER_ID, payload)


@router.get("/{watchlist_id}", response_model=WatchlistOut)
async def get_watchlist(watchlist_id: str, db: AsyncSession = Depends(get_db)):
    wl = await watchlist_service.get_watchlist(db, watchlist_id, DEMO_USER_ID)
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return wl


@router.delete("/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watchlist(watchlist_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await watchlist_service.delete_watchlist(db, watchlist_id, DEMO_USER_ID)
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
):
    item = await watchlist_service.add_symbol_to_watchlist(
        db, watchlist_id, DEMO_USER_ID, payload.symbol
    )
    if not item:
        raise HTTPException(
            status_code=404,
            detail=f"Symbol '{payload.symbol}' not found or watchlist does not exist",
        )
    return item


@router.delete("/{watchlist_id}/symbols/{symbol_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_symbol(
    watchlist_id: str,
    symbol_id: str,
    db: AsyncSession = Depends(get_db),
):
    removed = await watchlist_service.remove_symbol_from_watchlist(
        db, watchlist_id, DEMO_USER_ID, symbol_id
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
