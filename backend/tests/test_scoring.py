"""
Unit tests for the scoring engine.
"""
import pytest

from app.engine.scoring import (
    RawSignals,
    ScoredResult,
    _count_active_signals,
    compute_confidence,
    compute_raw_score,
    corroboration_boost,
    score,
)


class TestComputeRawScore:
    def test_all_zero_signals(self):
        s = RawSignals()
        assert compute_raw_score(s) == pytest.approx(0.0)

    def test_all_one_signals(self):
        s = RawSignals(price_move=1.0, volume_spike=1.0, relative_move=1.0, breakout=1.0, news_surge=1.0)
        raw = compute_raw_score(s)
        assert raw == pytest.approx(1.0, rel=1e-3)

    def test_weights_sum_to_one(self):
        """Weights must sum to 1 so that all-1 signals = score 1."""
        from app.config import settings
        total = (
            settings.weight_price_move
            + settings.weight_volume_spike
            + settings.weight_relative_move
            + settings.weight_breakout
            + settings.weight_news_surge
        )
        assert total == pytest.approx(1.0, abs=0.001)

    def test_highest_weight_is_price(self):
        from app.config import settings
        assert settings.weight_price_move == max(
            settings.weight_price_move,
            settings.weight_volume_spike,
            settings.weight_relative_move,
            settings.weight_breakout,
            settings.weight_news_surge,
        )


class TestCorroborationBoost:
    def test_zero_signals(self):
        assert corroboration_boost(0.5, 0) == 0.0

    def test_one_signal(self):
        assert corroboration_boost(0.5, 1) == 0.0

    def test_two_signals(self):
        boost = corroboration_boost(0.5, 2)
        assert boost == pytest.approx(0.025, rel=1e-3)

    def test_three_signals(self):
        boost = corroboration_boost(0.5, 3)
        assert boost == pytest.approx(0.05, rel=1e-3)

    def test_four_signals(self):
        boost = corroboration_boost(0.5, 4)
        assert boost == pytest.approx(0.075, rel=1e-3)


class TestAttentionLevels:
    def test_critical(self):
        s = RawSignals(price_move=1.0, volume_spike=1.0, relative_move=1.0, breakout=1.0, news_surge=1.0)
        result = score(s)
        assert result.attention_level == "CRITICAL"

    def test_no_change(self):
        s = RawSignals()
        result = score(s)
        assert result.attention_level == "NO_CHANGE"

    def test_watch_level(self):
        # Small but nonzero signals
        s = RawSignals(price_move=0.2, volume_spike=0.1)
        result = score(s)
        assert result.attention_level in ("WATCH", "NO_CHANGE")

    def test_stale_data_caps_critical(self):
        s = RawSignals(price_move=1.0, volume_spike=1.0, relative_move=1.0, breakout=1.0, news_surge=1.0)
        result = score(s, data_is_fresh=False)
        assert result.attention_level != "CRITICAL"


class TestComputeConfidence:
    def test_fresh_data_full_signals(self):
        s = RawSignals(price_move=1.0, volume_spike=1.0, relative_move=1.0, breakout=1.0, news_surge=1.0)
        c = compute_confidence(s, data_is_fresh=True)
        assert c == pytest.approx(1.0, abs=0.01)

    def test_stale_data_caps_confidence(self):
        s = RawSignals(price_move=1.0, volume_spike=1.0, relative_move=1.0, breakout=1.0, news_surge=1.0)
        c = compute_confidence(s, data_is_fresh=False)
        assert c <= 0.6

    def test_no_signals_low_confidence(self):
        s = RawSignals()
        c = compute_confidence(s, data_is_fresh=True)
        assert c <= 0.5
