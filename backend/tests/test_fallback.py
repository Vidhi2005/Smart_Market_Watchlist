"""
Tests for the LLM hallucination guard — this is the safety net that lets us
trust LLM-generated explanations enough to show them to users.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.llm.fallback import hallucination_check, template_explanation


class TestHallucinationCheck:
    def test_accepts_exact_matches(self):
        allowed = [2.19, 0.0, 3.2, 3.0]
        assert hallucination_check("Stock moved +2.19% on 3.2x volume.", allowed)

    def test_accepts_negative_percentage_matching_a_positive_magnitude(self):
        # A stock down 2.19% legitimately renders as "-2.19%" in prose, even
        # though the allowed list stores magnitudes (abs values). Regression
        # test for a bug where the sign was compared instead of magnitude —
        # this silently failed every down-move explanation and forced a
        # template fallback, without ever surfacing an error.
        allowed = [2.19, 0.0, 3.2, 3.0]
        assert hallucination_check("AAPL dropped -2.19% vs a flat market (+0.00%).", allowed)

    def test_rejects_invented_percentage(self):
        allowed = [2.19, 0.0, 3.2, 3.0]
        assert not hallucination_check("Stock surged +15.7% today.", allowed)

    def test_allows_small_tolerance(self):
        allowed = [2.19]
        assert hallucination_check("Stock moved 2.5% today.", allowed)  # within 0.5 tolerance

    def test_no_percentages_is_safe(self):
        assert hallucination_check("Stock showed notable activity.", [2.19])


class TestTemplateExplanation:
    def test_includes_direction_and_magnitude(self):
        text = template_explanation(
            symbol="AAPL", attention_level="HIGH", stock_pct_change=-2.19,
            bench_pct_change=0.0, volume_ratio=3.2, news_count_24h=3, breakout=0.2,
        )
        assert "AAPL" in text
        assert "down" in text
        assert "2.2%" in text  # abs(-2.19) rounded to 1dp


class TestGeminiClientBounds:
    """
    The Gemini call itself had no output-length enforcement and no timeout
    before this pass — output length was only a soft prompt instruction.
    These confirm the actual client.models.generate_content call site now
    passes a real max_output_tokens bound, and that a hung/slow call still
    resolves to the same None-on-failure fallback contract.
    """

    async def test_generate_content_is_called_with_max_output_tokens(self):
        from app.llm import client as llm_client

        fake_response = MagicMock()
        fake_response.text = "Stock moved on volume."
        fake_client = MagicMock()
        fake_client.models.generate_content.return_value = fake_response

        with patch.object(llm_client, "_get_client", return_value=fake_client):
            result = await llm_client.generate_explanation("some prompt")

        assert result == "Stock moved on volume."
        _, call_kwargs = fake_client.models.generate_content.call_args
        assert call_kwargs["config"].max_output_tokens == 80

    async def test_timeout_falls_back_to_none(self):
        from app.llm import client as llm_client

        def _hang(*args, **kwargs):
            import time
            time.sleep(1)

        fake_client = MagicMock()
        fake_client.models.generate_content.side_effect = _hang

        with patch.object(llm_client, "_get_client", return_value=fake_client), \
             patch("app.config.settings.gemini_timeout_seconds", 0.05):
            result = await llm_client.generate_explanation("some prompt")

        assert result is None
