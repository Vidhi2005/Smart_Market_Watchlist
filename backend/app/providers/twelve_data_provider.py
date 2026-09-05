"""
Twelve Data market data provider — live-verified secondary for the US
market (real quote/time-series data confirmed, free tier 800 req/day,
8 req/min). NOT used for India: live testing confirmed NSE symbols
(tried both `RELIANCE:NSE` and `symbol=RELIANCE&exchange=NSE` formats)
return "This symbol is available starting with the Grow or Venture
plan" — i.e. genuinely paywalled on the free tier, not just a wrong
symbol format. Left implemented and available in the provider registry
(so re-verifying after a plan change is a config edit, not new code) but
excluded from `india_provider_chain` by default.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import httpx

from app.providers.base import CandleData, MarketDataProvider, NewsItem, QuoteData

logger = logging.getLogger(__name__)

_BASE = "https://api.twelvedata.com"
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class TwelveDataProvider(MarketDataProvider):
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=_TIMEOUT)

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _get(self, path: str, params: dict) -> dict | None:
        """
        A single attempt, no retry loop (unlike Finnhub) — Twelve Data's
        free tier is 8 requests/minute, tight enough that burning retries
        on a already-scarce budget isn't worth it for a secondary
        provider that's only ever called after the primary has failed.
        Known-failure conditions (timeout, HTTP error, bad JSON, or the
        API's own {"status": "error"} envelope) all return None so the
        fallback chain moves on; anything else propagates as a real bug.
        """
        params = {**params, "apikey": self._api_key}
        try:
            resp = await self._client.get(f"{_BASE}{path}", params=params)
        except httpx.TimeoutException:
            logger.warning("Twelve Data timeout for %s", path)
            return None
        except httpx.HTTPError as exc:
            logger.warning("Twelve Data request error for %s: %s", path, exc)
            return None

        try:
            data = resp.json()
        except ValueError:
            logger.warning("Twelve Data returned non-JSON for %s", path)
            return None

        if resp.status_code == 429 or (isinstance(data, dict) and data.get("code") == 429):
            logger.warning("Twelve Data rate-limited for %s", path)
            return None
        if isinstance(data, dict) and data.get("status") == "error":
            logger.warning("Twelve Data error for %s: %s", path, data.get("message"))
            return None
        if resp.status_code >= 400:
            logger.warning("Twelve Data HTTP %s for %s", resp.status_code, path)
            return None

        return data

    # ── Quote ─────────────────────────────────────────────────────────────────

    async def get_quote(self, symbol: str) -> QuoteData | None:
        data = await self._get("/quote", {"symbol": symbol})
        if not data:
            return None

        try:
            price = Decimal(str(data["close"]))
            previous_close = Decimal(str(data.get("previous_close", data["close"])))
        except (KeyError, InvalidOperation, TypeError):
            logger.warning("Twelve Data quote missing/invalid price fields for %s", symbol)
            return None
        if price <= 0:
            return None

        ts = data.get("timestamp")
        provider_ts = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None

        def _dec(key: str) -> Decimal | None:
            v = data.get(key)
            try:
                return Decimal(str(v)) if v not in (None, "") else None
            except InvalidOperation:
                return None

        volume = data.get("volume")
        return QuoteData(
            symbol=symbol,
            price=price,
            previous_close=previous_close,
            open=_dec("open"),
            high=_dec("high"),
            low=_dec("low"),
            volume=int(float(volume)) if volume not in (None, "") else None,
            provider_timestamp=provider_ts,
            source="twelve_data",
        )

    # ── Company profile ──────────────────────────────────────────────────────

    async def get_company_name(self, symbol: str) -> str | None:
        data = await self._get("/quote", {"symbol": symbol})
        if not data:
            return None
        name = data.get("name")
        return name.strip() if name else None

    # ── Candles ───────────────────────────────────────────────────────────────

    _RESOLUTION_TO_INTERVAL = {"D": "1day", "60": "1h", "30": "30min", "15": "15min", "5": "5min", "1": "1min"}

    async def get_candles(
        self,
        symbol: str,
        from_ts: int,
        to_ts: int,
        resolution: str = "D",
    ) -> list[CandleData]:
        interval = self._RESOLUTION_TO_INTERVAL.get(resolution, "1day")
        span_days = max(1, (to_ts - from_ts) // 86400)
        data = await self._get(
            "/time_series",
            {"symbol": symbol, "interval": interval, "outputsize": min(span_days + 2, 5000)},
        )
        if not data:
            return []

        candles: list[CandleData] = []
        for row in data.get("values", []):
            try:
                candles.append(
                    CandleData(
                        symbol=symbol,
                        timestamp=datetime.strptime(row["datetime"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                        if len(row["datetime"]) == 10
                        else datetime.strptime(row["datetime"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc),
                        open=Decimal(str(row["open"])),
                        high=Decimal(str(row["high"])),
                        low=Decimal(str(row["low"])),
                        close=Decimal(str(row["close"])),
                        volume=int(float(row["volume"])) if row.get("volume") else 0,
                    )
                )
            except (KeyError, ValueError, InvalidOperation):
                continue

        return candles

    # ── News ──────────────────────────────────────────────────────────────────

    async def get_news(self, symbol: str, days_back: int = 7) -> list[NewsItem]:
        # Twelve Data's free tier has no news endpoint — this provider is
        # quote/candle-only. Returning [] keeps the interface satisfied
        # without pretending to a capability the free plan doesn't have.
        return []

    def news_dedup_hash(self, symbol: str, headline: str, published_at: datetime) -> str:
        raw = f"{symbol}|{headline.strip().lower()}|{published_at.date()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:64]

    async def close(self) -> None:
        await self._client.aclose()
