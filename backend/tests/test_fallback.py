"""
Tests for the LLM hallucination guard — this is the safety net that lets us
trust LLM-generated explanations enough to show them to users.
"""
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
