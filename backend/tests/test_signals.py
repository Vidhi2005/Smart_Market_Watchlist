"""
Unit tests for signal computation functions.
"""
import math
from decimal import Decimal

import pytest

from app.engine.signals import (
    breakout_signal,
    news_surge_signal,
    pct_change,
    price_move_signal,
    relative_move_signal,
    volume_spike_signal,
)


class TestPriceMoveSignal:
    def test_no_move(self):
        s = price_move_signal(Decimal("100"), Decimal("100"))
        assert s == pytest.approx(0.0, abs=1e-6)

    def test_small_move(self):
        # 0.5% move — should be a low score
        s = price_move_signal(Decimal("100.50"), Decimal("100"), typical_daily_move_pct=1.5)
        assert 0 < s < 0.3

    def test_large_move(self):
        # 10% move — should be near 1.0
        s = price_move_signal(Decimal("110"), Decimal("100"), typical_daily_move_pct=1.5)
        assert s > 0.9

    def test_negative_move(self):
        # Down moves count equally
        s_up = price_move_signal(Decimal("105"), Decimal("100"))
        s_down = price_move_signal(Decimal("95"), Decimal("100"))
        assert s_up == pytest.approx(s_down, rel=1e-4)

    def test_invalid_previous_close(self):
        assert price_move_signal(Decimal("100"), Decimal("0")) == 0.0

    def test_bounded(self):
        # Very large move stays ≤ 1
        s = price_move_signal(Decimal("200"), Decimal("100"))
        assert 0 <= s <= 1.0


class TestVolumeSpikeSignal:
    def test_no_volume(self):
        assert volume_spike_signal(0, 1_000_000) == 0.0

    def test_normal_volume(self):
        s = volume_spike_signal(1_000_000, 1_000_000)
        assert s == pytest.approx(0.0, abs=1e-6)

    def test_double_volume(self):
        s = volume_spike_signal(2_000_000, 1_000_000)
        assert 0.5 < s < 0.75

    def test_5x_volume(self):
        s = volume_spike_signal(5_000_000, 1_000_000)
        assert s > 0.9

    def test_bounded(self):
        s = volume_spike_signal(100_000_000, 1_000)
        assert 0 <= s <= 1.0


class TestRelativeMoveSignal:
    def test_same_as_market(self):
        s = relative_move_signal(1.0, 1.0)
        assert s == pytest.approx(0.0, abs=1e-6)

    def test_2pct_excess(self):
        s = relative_move_signal(3.0, 1.0)
        assert 0.5 < s < 0.8

    def test_10pct_excess(self):
        s = relative_move_signal(11.0, 1.0)
        assert s > 0.99

    def test_bounded(self):
        assert 0 <= relative_move_signal(50.0, 0.0) <= 1.0


class TestBreakoutSignal:
    def test_within_range(self):
        s = breakout_signal(Decimal("100"), Decimal("120"), Decimal("80"))
        # Middle of range — score should be at most 0.5
        assert s <= 0.5

    def test_at_high(self):
        s = breakout_signal(Decimal("120"), Decimal("120"), Decimal("80"))
        assert s == 1.0

    def test_at_low(self):
        s = breakout_signal(Decimal("80"), Decimal("120"), Decimal("80"))
        assert s == 1.0

    def test_near_high(self):
        s = breakout_signal(Decimal("118"), Decimal("120"), Decimal("80"))
        assert s > 0.7

    def test_bad_range(self):
        assert breakout_signal(Decimal("100"), Decimal("100"), Decimal("100")) == 0.0


class TestNewsSurgeSignal:
    def test_no_news(self):
        assert news_surge_signal(0) == 0.0

    def test_normal_news(self):
        s = news_surge_signal(2, avg_daily_news=2.0)
        assert s == pytest.approx(0.0, abs=0.01)

    def test_heavy_news(self):
        s = news_surge_signal(10, avg_daily_news=2.0)
        assert s > 0.85

    def test_bounded(self):
        assert 0 <= news_surge_signal(1000) <= 1.0


class TestPctChange:
    def test_positive(self):
        assert pct_change(Decimal("105"), Decimal("100")) == pytest.approx(5.0)

    def test_negative(self):
        assert pct_change(Decimal("90"), Decimal("100")) == pytest.approx(-10.0)

    def test_zero_base(self):
        assert pct_change(Decimal("100"), Decimal("0")) == 0.0
