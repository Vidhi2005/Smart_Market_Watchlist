"""
Tests for the provider fallback chain and cross-provider conflict
detection — real mechanisms that existed with zero test coverage before
this pass (get_quote_with_fallback existed but was untested; the
conflict check existed but only ever logged a warning and was never
exercised by a test either).
"""
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.providers.base import QuoteData
from app.services.watchlist_service import detect_price_conflict


def _quote(price: float, source: str) -> QuoteData:
    return QuoteData(
        symbol="TEST",
        price=Decimal(str(price)),
        previous_close=Decimal(str(price)),
        open=None,
        high=None,
        low=None,
        volume=None,
        provider_timestamp=None,
        source=source,
    )


class TestDetectPriceConflict:
    def test_agreement_within_tolerance_is_not_a_conflict(self):
        assert detect_price_conflict(100.0, 100.5) is None  # 0.5% apart

    def test_disagreement_beyond_tolerance_returns_diff_pct(self):
        result = detect_price_conflict(100.0, 105.0, tolerance_pct=2.0)
        assert result == pytest.approx(5.0)

    def test_exactly_at_tolerance_is_not_a_conflict(self):
        # Strictly greater-than tolerance, not >=, so the boundary itself
        # doesn't flag — avoids flapping right at the threshold.
        assert detect_price_conflict(100.0, 102.0, tolerance_pct=2.0) is None

    def test_zero_or_negative_canonical_price_returns_none(self):
        assert detect_price_conflict(0.0, 50.0) is None
        assert detect_price_conflict(-10.0, 50.0) is None


class TestQuoteFallbackChain:
    """
    Patches app.config.settings' chain strings directly rather than the
    provider classes' network calls, then patches each provider class's
    get_quote to simulate success/failure — this exercises the real
    chain-walking logic in _chain_for/get_quote_with_fallback_chain
    without hitting the network.
    """

    async def test_primary_success_never_calls_secondary(self):
        from app.services import ingestion_service as svc

        svc._provider_instances.clear()
        with patch("app.config.settings.us_provider_chain", "finnhub,twelve_data,yfinance"), \
             patch("app.config.settings.finnhub_api_key", "fake-key"), \
             patch("app.config.settings.twelve_data_api_key", "fake-key"), \
             patch(
                 "app.providers.finnhub_provider.FinnhubProvider.get_quote",
                 new=AsyncMock(return_value=_quote(100.0, "finnhub")),
             ) as finnhub_mock, \
             patch(
                 "app.providers.twelve_data_provider.TwelveDataProvider.get_quote",
                 new=AsyncMock(return_value=_quote(100.0, "twelve_data")),
             ) as td_mock:
            quote, tried = await svc.get_quote_with_fallback_chain("AAPL")

        assert quote is not None
        assert quote.source == "finnhub"
        assert tried == ["finnhub"]
        finnhub_mock.assert_awaited_once()
        td_mock.assert_not_awaited()
        svc._provider_instances.clear()

    async def test_primary_failure_falls_through_to_secondary(self):
        from app.services import ingestion_service as svc

        svc._provider_instances.clear()
        with patch("app.config.settings.us_provider_chain", "finnhub,twelve_data,yfinance"), \
             patch("app.config.settings.finnhub_api_key", "fake-key"), \
             patch("app.config.settings.twelve_data_api_key", "fake-key"), \
             patch(
                 "app.providers.finnhub_provider.FinnhubProvider.get_quote",
                 new=AsyncMock(return_value=None),
             ), \
             patch(
                 "app.providers.twelve_data_provider.TwelveDataProvider.get_quote",
                 new=AsyncMock(return_value=_quote(101.0, "twelve_data")),
             ):
            quote, tried = await svc.get_quote_with_fallback_chain("AAPL")

        assert quote is not None
        assert quote.source == "twelve_data"
        assert tried == ["finnhub", "twelve_data"]
        svc._provider_instances.clear()

    async def test_provider_raising_is_treated_like_returning_none(self):
        """A provider that raises (timeout/HTTP/parse error already caught
        *inside* its own adapter and turned into None) must not be special
        here — the chain only ever sees None-or-value from get_quote."""
        from app.services import ingestion_service as svc

        svc._provider_instances.clear()
        with patch("app.config.settings.us_provider_chain", "finnhub,twelve_data,yfinance"), \
             patch("app.config.settings.finnhub_api_key", "fake-key"), \
             patch("app.config.settings.twelve_data_api_key", "fake-key"), \
             patch(
                 "app.providers.finnhub_provider.FinnhubProvider.get_quote",
                 new=AsyncMock(return_value=None),  # adapter already caught its own exception
             ), \
             patch(
                 "app.providers.twelve_data_provider.TwelveDataProvider.get_quote",
                 new=AsyncMock(return_value=None),
             ), \
             patch(
                 "app.providers.yfinance_provider.YFinanceProvider.get_quote",
                 new=AsyncMock(return_value=_quote(99.0, "yfinance")),
             ):
            quote, tried = await svc.get_quote_with_fallback_chain("AAPL")

        assert quote is not None
        assert quote.source == "yfinance"
        assert tried == ["finnhub", "twelve_data", "yfinance"]
        svc._provider_instances.clear()

    async def test_all_providers_failing_returns_none_with_full_tried_list(self):
        from app.services import ingestion_service as svc

        svc._provider_instances.clear()
        with patch("app.config.settings.us_provider_chain", "finnhub,yfinance"), \
             patch("app.config.settings.finnhub_api_key", "fake-key"), \
             patch(
                 "app.providers.finnhub_provider.FinnhubProvider.get_quote",
                 new=AsyncMock(return_value=None),
             ), \
             patch(
                 "app.providers.yfinance_provider.YFinanceProvider.get_quote",
                 new=AsyncMock(return_value=None),
             ):
            quote, tried = await svc.get_quote_with_fallback_chain("AAPL")

        assert quote is None
        assert tried == ["finnhub", "yfinance"]
        svc._provider_instances.clear()

    async def test_provider_without_configured_key_is_skipped_entirely(self):
        """Alpha Vantage listed in the chain but with no key configured
        must never be constructed/called — only its *presence in the
        chain string* matters for whether it's ever attempted, and an
        empty key must still exclude it even if listed."""
        from app.services import ingestion_service as svc

        svc._provider_instances.clear()
        with patch("app.config.settings.us_provider_chain", "finnhub,alpha_vantage,yfinance"), \
             patch("app.config.settings.finnhub_api_key", "fake-key"), \
             patch("app.config.settings.alpha_vantage_api_key", ""), \
             patch(
                 "app.providers.finnhub_provider.FinnhubProvider.get_quote",
                 new=AsyncMock(return_value=None),
             ), \
             patch(
                 "app.providers.yfinance_provider.YFinanceProvider.get_quote",
                 new=AsyncMock(return_value=_quote(98.0, "yfinance")),
             ):
            quote, tried = await svc.get_quote_with_fallback_chain("AAPL")

        assert quote is not None
        assert "alpha_vantage" not in tried
        assert tried == ["finnhub", "yfinance"]
        svc._provider_instances.clear()
