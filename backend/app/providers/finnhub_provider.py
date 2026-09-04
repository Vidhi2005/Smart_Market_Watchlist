"""
Finnhub market data provider with rate-limit handling and retry logic.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx

from app.providers.base import CandleData, MarketDataProvider, NewsItem, QuoteData

logger = logging.getLogger(__name__)

_BASE = "https://finnhub.io/api/v1"
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0  # seconds


class FinnhubProvider(MarketDataProvider):
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=_TIMEOUT)

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _get(self, path: str, params: dict) -> dict | list | None:
        """GET with exponential backoff on 429 / transient errors."""
        params["token"] = self._api_key
        url = f"{_BASE}{path}"

        for attempt in range(_MAX_RETRIES):
            try:
                resp = await self._client.get(url, params=params)
                if resp.status_code == 429:
                    wait = _BACKOFF_BASE ** attempt
                    logger.warning("Finnhub rate-limited — sleeping %.1fs", wait)
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.TimeoutException:
                wait = _BACKOFF_BASE ** attempt
                logger.warning("Finnhub timeout for %s (attempt %d) — retry in %.1fs", path, attempt + 1, wait)
                await asyncio.sleep(wait)
            except httpx.HTTPStatusError as exc:
                logger.error("Finnhub HTTP error %s for %s", exc.response.status_code, path)
                return None
            except Exception as exc:  # noqa: BLE001
                logger.error("Finnhub unexpected error: %s", exc)
                return None

        logger.error("Finnhub: exhausted retries for %s", path)
        return None

    # ── Quote ─────────────────────────────────────────────────────────────────

    async def get_quote(self, symbol: str) -> QuoteData | None:
        data = await self._get("/quote", {"symbol": symbol})
        if not data or not isinstance(data, dict):
            return None

        price = data.get("c", 0)
        if not price or price <= 0:
            logger.warning("Invalid quote for %s: price=%s", symbol, price)
            return None

        ts = data.get("t")
        provider_ts = (
            datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None
        )

        return QuoteData(
            symbol=symbol,
            price=Decimal(str(price)),
            previous_close=Decimal(str(data.get("pc", price))),
            open=Decimal(str(data.get("o"))) if data.get("o") else None,
            high=Decimal(str(data.get("h"))) if data.get("h") else None,
            low=Decimal(str(data.get("l"))) if data.get("l") else None,
            volume=int(data.get("v", 0)) if data.get("v") else None,
            provider_timestamp=provider_ts,
            source="finnhub",
        )

    # ── Company profile ──────────────────────────────────────────────────────

    async def get_company_name(self, symbol: str) -> str | None:
        data = await self._get("/stock/profile2", {"symbol": symbol})
        if not data or not isinstance(data, dict):
            return None
        name = data.get("name")
        return name.strip() if name else None

    # ── Candles ───────────────────────────────────────────────────────────────

    async def get_candles(
        self,
        symbol: str,
        from_ts: int,
        to_ts: int,
        resolution: str = "D",
    ) -> list[CandleData]:
        data = await self._get(
            "/stock/candle",
            {"symbol": symbol, "resolution": resolution, "from": from_ts, "to": to_ts},
        )
        if not data or isinstance(data, dict) and data.get("s") != "ok":
            return []

        closes = data.get("c", [])
        opens = data.get("o", [])
        highs = data.get("h", [])
        lows = data.get("l", [])
        volumes = data.get("v", [])
        timestamps = data.get("t", [])

        candles: list[CandleData] = []
        for i, ts in enumerate(timestamps):
            try:
                candles.append(
                    CandleData(
                        symbol=symbol,
                        timestamp=datetime.fromtimestamp(ts, tz=timezone.utc),
                        open=Decimal(str(opens[i])),
                        high=Decimal(str(highs[i])),
                        low=Decimal(str(lows[i])),
                        close=Decimal(str(closes[i])),
                        volume=int(volumes[i]) if volumes else 0,
                    )
                )
            except (IndexError, ValueError):
                continue

        return candles

    # ── News ──────────────────────────────────────────────────────────────────

    async def get_news(self, symbol: str, days_back: int = 7) -> list[NewsItem]:
        to_dt = datetime.now(tz=timezone.utc)
        from_dt = to_dt - timedelta(days=days_back)
        data = await self._get(
            "/company-news",
            {
                "symbol": symbol,
                "from": from_dt.strftime("%Y-%m-%d"),
                "to": to_dt.strftime("%Y-%m-%d"),
            },
        )
        if not data or not isinstance(data, list):
            return []

        items: list[NewsItem] = []
        for raw in data[:50]:  # cap at 50 items per call
            headline = raw.get("headline", "").strip()
            if not headline:
                continue
            ts = raw.get("datetime")
            published_at = (
                datetime.fromtimestamp(ts, tz=timezone.utc)
                if ts
                else datetime.now(tz=timezone.utc)
            )
            items.append(
                NewsItem(
                    symbol=symbol,
                    headline=headline,
                    summary=raw.get("summary"),
                    source=raw.get("source"),
                    url=raw.get("url"),
                    published_at=published_at,
                )
            )
        return items

    def news_dedup_hash(self, symbol: str, headline: str, published_at: datetime) -> str:
        """Deterministic hash for deduplication."""
        raw = f"{symbol}|{headline.strip().lower()}|{published_at.date()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:64]

    async def close(self) -> None:
        await self._client.aclose()
