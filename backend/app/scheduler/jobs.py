"""
APScheduler jobs — market data poll and news ingestion.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def create_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = AsyncIOScheduler()

    # Market data poll every POLL_INTERVAL_SECONDS
    _scheduler.add_job(
        _safe_poll_market,
        trigger=IntervalTrigger(seconds=settings.poll_interval_seconds),
        id="poll_market_data",
        replace_existing=True,
    )

    # News poll every 10 minutes
    _scheduler.add_job(
        _safe_poll_news,
        trigger=IntervalTrigger(minutes=10),
        id="poll_news",
        replace_existing=True,
    )

    return _scheduler


async def _safe_poll_market() -> None:
    """Wrapped poll that guards against crashes killing the scheduler."""
    from app.engine.market_calendar import is_market_open
    if not is_market_open():
        logger.debug("Market closed — skipping poll.")
        return
    try:
        from app.services.ingestion_service import poll_market_data
        await poll_market_data()
    except Exception as exc:  # noqa: BLE001
        logger.error("poll_market_data failed: %s", exc)


async def _safe_poll_news() -> None:
    try:
        from app.services.ingestion_service import poll_news
        await poll_news()
    except Exception as exc:  # noqa: BLE001
        logger.error("poll_news failed: %s", exc)
