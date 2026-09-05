"""
Alpha Vantage market data provider — live-verified to return real,
accurate US quote and daily time-series data. NOT wired into any
provider chain by default: its free tier is a hard 25 requests/day
total (confirmed live), which can't sustain sitting in an active
polling fallback path — even a single symbol polled continuously at
this app's cadence would need roughly two orders of magnitude more
requests per day than that budget allows. Kept implemented and
available in the provider registry for the option of very sparing,
deliberate use (e.g. a manual one-off check) rather than deleted, since
the capability is real even though the quota rules out routine use.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import httpx

from app.providers.base import CandleData, MarketDataProvider, NewsItem, QuoteData

logger = logging.getLogger(__name__)

_BASE = "https://www.alphavantage.co/query"
_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


class AlphaVantageProvider(MarketDataProvider):
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=_TIMEOUT)

    async def _get(self, params: dict) -> dict | None:
        params = {**params, "apikey": self._api_key}
        try:
            resp = await self._client.get(_BASE, params=params)
        except httpx.TimeoutException:
            logger.warning("Alpha Vantage timeout for function=%s", params.get("function"))
            return None
        except httpx.HTTPError as exc:
            logger.warning("Alpha Vantage request error: %s", exc)
            return None

        try:
            data = resp.json()
        except ValueError:
            logger.warning("Alpha Vantage returned non-JSON response")
            return None

        # Alpha Vantage signals rate-limiting/quota exhaustion via a "Note"
        # or "Information" field in an otherwise-200 response, not an HTTP
        # status code — this is the one provider-specific quirk that
        # matters here, since it's the exact failure mode this adapter
        # exists to be recognized as "unavailable" rather than misread as
        # "symbol not found."
        if "Note" in data or "Information" in data:
            logger.warning("Alpha Vantage quota/rate message: %s", data.get("Note") or data.get("Information"))
            return None
        if resp.status_code >= 400:
            logger.warning("Alpha Vantage HTTP %s", resp.status_code)
            return None

        return data

    async def get_quote(self, symbol: str) -> QuoteData | None:
        data = await self._get({"function": "GLOBAL_QUOTE", "symbol": symbol})
        if not data:
            return None
        quote = data.get("Global Quote")
        if not quote:
            return None

        try:
            price = Decimal(str(quote["05. price"]))
            previous_close = Decimal(str(quote.get("08. previous close", quote["05. price"])))
        except (KeyError, InvalidOperation, TypeError):
            return None
        if price <= 0:
            return None

        def _dec(key: str) -> Decimal | None:
            v = quote.get(key)
            try:
                return Decimal(str(v)) if v not in (None, "") else None
            except InvalidOperation:
                return None

        volume = quote.get("06. volume")
        trading_day = quote.get("07. latest trading day")
        provider_ts = (
            datetime.strptime(trading_day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if trading_day
            else None
        )

        return QuoteData(
            symbol=symbol,
            price=price,
            previous_close=previous_close,
            open=_dec("02. open"),
            high=_dec("03. high"),
            low=_dec("04. low"),
            volume=int(volume) if volume else None,
            provider_timestamp=provider_ts,
            source="alpha_vantage",
        )

    async def get_company_name(self, symbol: str) -> str | None:
        # GLOBAL_QUOTE doesn't return a company name; OVERVIEW does but
        # costs a separate request against the same 25/day budget — not
        # worth spending on a provider that isn't in the active chain.
        return None

    async def get_candles(
        self,
        symbol: str,
        from_ts: int,
        to_ts: int,
        resolution: str = "D",
    ) -> list[CandleData]:
        data = await self._get({
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": "compact",
        })
        if not data:
            return []
        series = data.get("Time Series (Daily)")
        if not series:
            return []

        candles: list[CandleData] = []
        for date_str, row in series.items():
            try:
                ts = int(datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
                if not (from_ts <= ts <= to_ts):
                    continue
                candles.append(
                    CandleData(
                        symbol=symbol,
                        timestamp=datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc),
                        open=Decimal(str(row["1. open"])),
                        high=Decimal(str(row["2. high"])),
                        low=Decimal(str(row["3. low"])),
                        close=Decimal(str(row["4. close"])),
                        volume=int(row["5. volume"]) if row.get("5. volume") else 0,
                    )
                )
            except (KeyError, ValueError, InvalidOperation):
                continue

        return sorted(candles, key=lambda c: c.timestamp)

    async def get_news(self, symbol: str, days_back: int = 7) -> list[NewsItem]:
        # Alpha Vantage's News & Sentiment endpoint exists but isn't part
        # of this pass (news fallback is explicitly out of scope) and
        # would compete for the same 25/day quote budget — not worth it.
        return []

    def news_dedup_hash(self, symbol: str, headline: str, published_at: datetime) -> str:
        raw = f"{symbol}|{headline.strip().lower()}|{published_at.date()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:64]

    async def close(self) -> None:
        await self._client.aclose()
