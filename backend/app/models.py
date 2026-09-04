"""
SQLAlchemy ORM models — mirrors the schema.sql tables exactly.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ── users ─────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    # IANA timezone (e.g. "Asia/Kolkata") — drives timezone-correct UI like
    # the dashboard's time-of-day greeting. Defaults to UTC so a missing
    # value never crashes formatting, just shows a neutral greeting.
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    watchlists: Mapped[List["Watchlist"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    observations: Mapped[List["UserObservation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


# ── symbols ───────────────────────────────────────────────────────────────────
class Symbol(Base):
    __tablename__ = "symbols"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[Optional[str]] = mapped_column(String(100))
    exchange: Mapped[Optional[str]] = mapped_column(String(50))

    snapshots: Mapped[List["MarketSnapshot"]] = relationship(
        back_populates="symbol", cascade="all, delete-orphan"
    )
    news_events: Mapped[List["NewsEvent"]] = relationship(
        back_populates="symbol", cascade="all, delete-orphan"
    )
    market_events: Mapped[List["MarketEvent"]] = relationship(
        back_populates="symbol", cascade="all, delete-orphan"
    )


# ── watchlists ────────────────────────────────────────────────────────────────
class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="My Watchlist")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="watchlists")
    items: Mapped[List["WatchlistItem"]] = relationship(
        back_populates="watchlist", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_watchlists_user_id", "user_id"),
    )


# ── watchlist_items ───────────────────────────────────────────────────────────
class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    watchlist_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("watchlists.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("symbols.id", ondelete="CASCADE"),
        nullable=False,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    watchlist: Mapped["Watchlist"] = relationship(back_populates="items")
    symbol: Mapped["Symbol"] = relationship()

    __table_args__ = (
        UniqueConstraint("watchlist_id", "symbol_id"),
        Index("idx_watchlist_items_watchlist", "watchlist_id"),
        Index("idx_watchlist_items_symbol", "symbol_id"),
    )


# ── market_snapshots ──────────────────────────────────────────────────────────
class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    symbol_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("symbols.id", ondelete="CASCADE"),
        nullable=False,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    volume: Mapped[Optional[int]] = mapped_column(BigInteger)
    previous_close: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    open: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    high: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    low: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="finnhub")
    provider_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    quality_status: Mapped[str] = mapped_column(String(20), nullable=False, default="FRESH")

    symbol: Mapped["Symbol"] = relationship(back_populates="snapshots")

    __table_args__ = (
        Index("idx_snapshots_symbol_time", "symbol_id", "ingested_at"),
    )


# ── news_events ───────────────────────────────────────────────────────────────
class NewsEvent(Base):
    __tablename__ = "news_events"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    symbol_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("symbols.id", ondelete="CASCADE"),
        nullable=False,
    )
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[Optional[str]] = mapped_column(String(100))
    url: Mapped[Optional[str]] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    dedup_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    symbol: Mapped["Symbol"] = relationship(back_populates="news_events")

    __table_args__ = (
        Index("idx_news_symbol_time", "symbol_id", "published_at"),
    )


# ── market_events ─────────────────────────────────────────────────────────────
class MarketEvent(Base):
    __tablename__ = "market_events"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    symbol_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("symbols.id", ondelete="CASCADE"),
        nullable=False,
    )
    snapshot_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("market_snapshots.id", ondelete="SET NULL"),
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    magnitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    signals: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    symbol: Mapped["Symbol"] = relationship(back_populates="market_events")
    attention_records: Mapped[List["UserAttention"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_events_symbol_time", "symbol_id", "detected_at"),
    )


# ── user_observations ─────────────────────────────────────────────────────────
class UserObservation(Base):
    __tablename__ = "user_observations"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    symbol_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("symbols.id", ondelete="CASCADE"),
        primary_key=True,
    )
    last_observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    last_observed_snapshot_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("market_snapshots.id", ondelete="SET NULL"),
    )

    user: Mapped["User"] = relationship(back_populates="observations")
    symbol: Mapped["Symbol"] = relationship()
    last_snapshot: Mapped["MarketSnapshot | None"] = relationship()


# ── user_attention ────────────────────────────────────────────────────────────
class UserAttention(Base):
    __tablename__ = "user_attention"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("market_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    score: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False, default=Decimal("1.0"))
    attention_level: Mapped[str] = mapped_column(String(20), nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text)
    explanation_source: Mapped[str] = mapped_column(String(20), nullable=False, default="template")
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    event: Mapped["MarketEvent"] = relationship(back_populates="attention_records")

    __table_args__ = (
        UniqueConstraint("user_id", "event_id"),
        Index("idx_attention_user_score", "user_id", "score"),
    )
