"""
FastAPI application entry point.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.auth import router as auth_router
from app.routers.dashboard import router as dashboard_router
from app.routers.health import router as health_router
from app.routers.watchlists import router as watchlist_router
from app.routers.watchlists import stock_router

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
# httpx's own request logger logs full URLs at INFO level, query string
# included — every provider adapter passes its API key as a query param
# (Finnhub's `token=`, Twelve Data's `apikey=`, Alpha Vantage's
# `apikey=`), so this was silently writing every key to the log file on
# every single request. WARNING still surfaces genuine httpx-level
# problems without echoing request URLs.
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start scheduler on startup, shut it down on exit."""
    from app.scheduler.jobs import create_scheduler
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler started. Poll interval: %ds", settings.poll_interval_seconds)
    yield
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped.")


app = FastAPI(
    title="Smart Market Watchlist",
    description="AI-powered attention engine for your stock watchlist.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(health_router, prefix="/api")
app.include_router(watchlist_router)
app.include_router(stock_router)
app.include_router(dashboard_router)


@app.get("/")
async def root():
    return {"message": "Smart Market Watchlist API", "docs": "/docs"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
