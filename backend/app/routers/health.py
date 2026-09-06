"""
Health check router.
"""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import HealthResponse, IngestionStats

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:  # noqa: BLE001
        # Logged server-side only — the raw exception can include
        # connection-string-adjacent detail (host, driver error text) that
        # a public, unauthenticated endpoint shouldn't echo back.
        logger.error("Health check DB connectivity failure: %s", exc)
        db_status = "error"

    from app.services.ingestion_service import ingestion_stats

    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        db=db_status,
        ingestion=IngestionStats(**ingestion_stats),
    )
