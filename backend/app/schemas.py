"""
Pydantic schemas for request/response validation.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, Any, List, Dict

from pydantic import BaseModel, ConfigDict, Field


# ── Shared ────────────────────────────────────────────────────────────────────
class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Auth ──────────────────────────────────────────────────────────────────────
class UserOut(OrmBase):
    id: str
    email: str
    display_name: str
    country: Optional[str] = None
    timezone: str = "UTC"
    created_at: datetime


class SignupRequest(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    timezone: Optional[str] = Field(default=None, max_length=50)


class LoginRequest(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(max_length=128)


class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    timezone: Optional[str] = Field(default=None, max_length=50)


class TokenResponse(BaseModel):
    token: str
    user: UserOut


# ── Symbol ────────────────────────────────────────────────────────────────────
class SymbolOut(OrmBase):
    id: str
    symbol: str
    company_name: str
    sector: Optional[str]
    exchange: Optional[str]


class SymbolSearchResult(BaseModel):
    symbol: str
    company_name: str
    sector: Optional[str] = None
    exchange: Optional[str] = None


# ── Watchlist ─────────────────────────────────────────────────────────────────
class WatchlistCreate(BaseModel):
    name: str = Field(default="My Watchlist", max_length=100)



class ProviderOutlierOut(BaseModel):
    provider: str
    price: float
    diff_pct: float


class ProviderConflictOut(BaseModel):
    """
    Only ever present on the response to adding a brand-new ticker — a
    one-time, symbol-resolution-time cross-provider check, not a
    persistent or continuously-recomputed field. Absent (None) means
    either the symbol already existed (no new provider call made) or
    every provider checked agreed within tolerance.
    """
    providers_checked: int
    canonical_provider: str
    canonical_price: float
    conflicting: bool
    outliers: List[ProviderOutlierOut]


class WatchlistItemOut(OrmBase):
    id: str
    symbol: SymbolOut
    added_at: datetime
    provider_conflict: Optional[ProviderConflictOut] = None


class WatchlistOut(OrmBase):
    id: str
    name: str
    created_at: datetime
    items: List[WatchlistItemOut] = []


class AddSymbolRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)


# ── Market Snapshot ───────────────────────────────────────────────────────────
class SnapshotOut(OrmBase):
    id: str
    price: Decimal
    volume: Optional[int]
    previous_close: Optional[Decimal]
    quality_status: str
    ingested_at: datetime


# ── News Event ────────────────────────────────────────────────────────────────
class NewsEventOut(OrmBase):
    id: str
    headline: str
    summary: Optional[str]
    source: Optional[str]
    url: Optional[str]
    published_at: datetime


# ── Market Event ──────────────────────────────────────────────────────────────
class MarketEventOut(OrmBase):
    id: str
    event_type: str
    magnitude: Optional[Decimal]
    signals: Dict[str, Any]
    detected_at: datetime


# ── Attention ─────────────────────────────────────────────────────────────────
class SignalBreakdown(BaseModel):
    """Individual signal values for frontend rendering."""
    price_move: float = 0.0
    volume_spike: float = 0.0
    relative_move: float = 0.0
    breakout: float = 0.0
    news_surge: float = 0.0
    corroboration_boost: float = 0.0


class AttentionItem(BaseModel):
    """One attention card — what the user sees on the dashboard."""
    symbol: str
    symbol_id: str
    company_name: str
    sector: Optional[str]
    attention_level: str           # CRITICAL | HIGH | WATCH
    score: float
    confidence: float
    explanation: str
    explanation_source: str        # llm | template
    event_type: str
    magnitude: Optional[float]
    current_price: Optional[Decimal]
    price_change_pct: Optional[float]           # vs previous_close ("today's move")
    since_checked_change_pct: Optional[float] = None  # vs the user's own baseline
    volume: Optional[int]
    avg_volume_30d: Optional[float] = None
    benchmark_change_pct: Optional[float] = None
    latest_news: List[NewsEventOut]
    signals: SignalBreakdown
    detected_at: datetime
    data_freshness: str            # FRESH | STALE


class ChangesResponse(BaseModel):
    watchlist_id: str
    user_id: str
    items: List[AttentionItem]
    all_caught_up: bool
    generated_at: datetime


# ── Dashboard ─────────────────────────────────────────────────────────────────
class DashboardSummary(BaseModel):
    total_symbols_tracked: int
    symbols_with_events: int
    critical_count: int
    high_count: int
    watch_count: int
    last_poll_at: Optional[datetime]
    last_checked_at: Optional[datetime] = None
    market_open: bool
    us_market_open: bool = False
    indian_market_open: bool = False


# ── Quotes (live market info, independent of attention scoring) ───────────────
class QuoteOut(BaseModel):
    symbol: str
    company_name: str
    sector: Optional[str]
    exchange: Optional[str]
    current_price: Optional[Decimal]
    price_change_pct: Optional[float]
    volume: Optional[int]
    data_freshness: str  # FRESH | STALE | NO_DATA


# ── Candles ───────────────────────────────────────────────────────────────────
class CandlePoint(BaseModel):
    timestamp: datetime
    price: Decimal
    volume: Optional[int] = None


class CandlesResponse(BaseModel):
    symbol: str
    range: str
    points: List[CandlePoint]


# ── Observation ───────────────────────────────────────────────────────────────
class CommitObservationsRequest(BaseModel):
    watchlist_id: str
    # None = commit all symbols in watchlist. max_length bounds the batched
    # IN (...) query cost — 500 comfortably exceeds any realistic watchlist.
    symbol_ids: List[str] | None = Field(default=None, max_length=500)


# ── Health ────────────────────────────────────────────────────────────────────
class IngestionStats(BaseModel):
    """Real operational counters — not a metrics platform, just enough to
    answer "is ingestion actually working" from the outside."""
    last_poll_started_at: Optional[datetime] = None
    last_poll_completed_at: Optional[datetime] = None
    last_poll_duration_seconds: Optional[float] = None
    last_poll_symbols_processed: int = 0
    last_poll_provider_failures: int = 0
    last_poll_fallback_used: int = 0
    provider_failures: dict[str, int] = {}
    llm_calls_total: int = 0
    llm_fallback_total: int = 0


class HealthResponse(BaseModel):
    status: str
    db: str
    version: str = "1.0.0"
    ingestion: IngestionStats = IngestionStats()
