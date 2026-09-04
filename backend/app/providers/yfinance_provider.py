"""
Yahoo Finance market data provider.

Supports:
  - Indian NSE stocks   e.g.  RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS
  - Indian BSE stocks   e.g.  RELIANCE.BO, TCS.BO
  - Any other Yahoo Finance ticker (US, crypto, indices …)

No API key required — completely free.
Runs yfinance in an executor thread so the async app stays non-blocking.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.providers.base import CandleData, MarketDataProvider, NewsItem, QuoteData

logger = logging.getLogger(__name__)


class YFinanceProvider(MarketDataProvider):
    """
    Thin async wrapper around yfinance.Ticker.
    yfinance is sync-only, so every call is dispatched to the default executor.
    """

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _run_sync(fn):
        """Run a blocking callable in the event-loop's thread-pool executor."""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, fn)

    # ── Quote ─────────────────────────────────────────────────────────────────

    async def get_quote(self, symbol: str) -> QuoteData | None:
        try:
            import yfinance as yf

            def _fetch():
                t = yf.Ticker(symbol)
                info = t.fast_info          # lightweight — avoids huge info dict
                return info

            info = await self._run_sync(_fetch)

            price = getattr(info, "last_price", None)
            prev  = getattr(info, "previous_close", None)
            if not price or price <= 0:
                logger.warning("YFinance: no valid price for %s (got %s)", symbol, price)
                return None

            return QuoteData(
                symbol=symbol,
                price=Decimal(str(round(price, 4))),
                previous_close=Decimal(str(round(prev, 4))) if prev else Decimal(str(round(price, 4))),
                open=Decimal(str(round(getattr(info, "open", price), 4))),
                high=Decimal(str(round(getattr(info, "day_high", price), 4))),
                low=Decimal(str(round(getattr(info, "day_low", price), 4))),
                volume=int(getattr(info, "last_volume", 0) or 0),
                provider_timestamp=datetime.now(tz=timezone.utc),
                source="yfinance",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("YFinance get_quote failed for %s: %s", symbol, exc)
            return None

    # ── Company profile ──────────────────────────────────────────────────────

    async def get_company_name(self, symbol: str) -> str | None:
        try:
            import yfinance as yf

            def _fetch():
                t = yf.Ticker(symbol)
                info = t.info  # heavier call, but only used once at add-time
                return info.get("longName") or info.get("shortName")

            name = await self._run_sync(_fetch)
            return name.strip() if name else None
        except Exception as exc:  # noqa: BLE001
            logger.warning("YFinance get_company_name failed for %s: %s", symbol, exc)
            return None

    # ── Candles ───────────────────────────────────────────────────────────────

    async def get_candles(
        self,
        symbol: str,
        from_ts: int,
        to_ts: int,
        resolution: str = "D",
    ) -> list[CandleData]:
        try:
            import yfinance as yf

            start = datetime.fromtimestamp(from_ts, tz=timezone.utc).strftime("%Y-%m-%d")
            end   = datetime.fromtimestamp(to_ts,   tz=timezone.utc).strftime("%Y-%m-%d")

            # Map Finnhub resolutions → yfinance intervals
            interval_map = {
                "D": "1d",
                "W": "1wk",
                "M": "1mo",
                "60": "1h",
                "30": "30m",
                "15": "15m",
                "5":  "5m",
                "1":  "1m",
            }
            interval = interval_map.get(resolution, "1d")

            def _fetch():
                t = yf.Ticker(symbol)
                return t.history(start=start, end=end, interval=interval, auto_adjust=True)

            df = await self._run_sync(_fetch)
            if df is None or df.empty:
                return []

            candles: list[CandleData] = []
            for ts, row in df.iterrows():
                # pandas Timestamp → aware datetime
                if hasattr(ts, "to_pydatetime"):
                    dt = ts.to_pydatetime()
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = datetime.now(tz=timezone.utc)

                candles.append(
                    CandleData(
                        symbol=symbol,
                        timestamp=dt,
                        open=Decimal(str(round(float(row["Open"]),  4))),
                        high=Decimal(str(round(float(row["High"]),  4))),
                        low=Decimal(str(round(float(row["Low"]),   4))),
                        close=Decimal(str(round(float(row["Close"]), 4))),
                        volume=int(row.get("Volume", 0) or 0),
                    )
                )
            return candles

        except Exception as exc:  # noqa: BLE001
            logger.warning("YFinance get_candles failed for %s: %s", symbol, exc)
            return []

    # ── News ──────────────────────────────────────────────────────────────────

    async def get_news(self, symbol: str, days_back: int = 7) -> list[NewsItem]:
        """
        yfinance exposes news via Ticker.news — a list of dicts.
        We filter to items published within the last `days_back` days.
        """
        try:
            import yfinance as yf

            def _fetch():
                t = yf.Ticker(symbol)
                return t.news

            raw_news = await self._run_sync(_fetch)
            if not raw_news:
                return []

            cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days_back)
            items: list[NewsItem] = []
            for raw in raw_news[:50]:
                content = raw.get("content", {})
                title = content.get("title") or raw.get("title", "").strip()
                if not title:
                    continue

                # Published timestamp — yfinance can store it in different places
                pub_ts = (
                    content.get("pubDate")
                    or raw.get("providerPublishTime")
                )
                if isinstance(pub_ts, str):
                    try:
                        from datetime import datetime as _dt
                        published_at = _dt.fromisoformat(pub_ts.replace("Z", "+00:00"))
                    except ValueError:
                        published_at = datetime.now(tz=timezone.utc)
                elif isinstance(pub_ts, (int, float)):
                    published_at = datetime.fromtimestamp(pub_ts, tz=timezone.utc)
                else:
                    published_at = datetime.now(tz=timezone.utc)

                if published_at < cutoff:
                    continue

                provider = content.get("provider", {})
                source = provider.get("displayName") if isinstance(provider, dict) else None

                click_urls = content.get("clickThroughUrl") or {}
                url = click_urls.get("url") if isinstance(click_urls, dict) else raw.get("link")

                summary = content.get("summary") or raw.get("summary") or None

                items.append(
                    NewsItem(
                        symbol=symbol,
                        headline=title,
                        summary=summary,
                        source=source,
                        url=url,
                        published_at=published_at,
                    )
                )
            return items

        except Exception as exc:  # noqa: BLE001
            logger.warning("YFinance get_news failed for %s: %s", symbol, exc)
            return []

    # ── Dedup hash (same signature as FinnhubProvider) ────────────────────────

    def news_dedup_hash(self, symbol: str, headline: str, published_at: datetime) -> str:
        raw = f"{symbol}|{headline.strip().lower()}|{published_at.date()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:64]

    async def close(self) -> None:
        pass  # nothing to close for yfinance
