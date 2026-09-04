"""
Abstract base classes for market data providers.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class QuoteData:
    symbol: str
    price: Decimal
    previous_close: Decimal
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    volume: int | None
    provider_timestamp: datetime | None
    source: str


@dataclass
class CandleData:
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


@dataclass
class NewsItem:
    symbol: str
    headline: str
    summary: str | None
    source: str | None
    url: str | None
    published_at: datetime


class MarketDataProvider(ABC):
    @abstractmethod
    async def get_quote(self, symbol: str) -> QuoteData | None:
        ...

    @abstractmethod
    async def get_company_name(self, symbol: str) -> str | None:
        """Best-effort company name lookup, used when resolving a ticker
        that isn't already in the local symbols catalog."""
        ...

    @abstractmethod
    async def get_candles(
        self,
        symbol: str,
        from_ts: int,
        to_ts: int,
        resolution: str = "D",
    ) -> list[CandleData]:
        ...

    @abstractmethod
    async def get_news(self, symbol: str, days_back: int = 7) -> list[NewsItem]:
        ...
