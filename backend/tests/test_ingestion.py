"""
Tests for the volume-baseline selection logic — the fix for "30-day average
volume" not actually being a clean daily average when live-poll rows (which
can carry intraday-cumulative or absent volume) get mixed in with real
daily bars.
"""
from app.services.ingestion_service import _select_volume_baseline


class TestSelectVolumeBaseline:
    def test_prefers_daily_bars_when_enough_exist(self):
        rows = [
            (1_000_000, True), (1_100_000, True), (1_050_000, True),  # daily bars
            (50_000, False), (60_000, False),  # noisy live-poll readings
        ]
        # Should average only the daily bars, ignoring the live-poll noise.
        assert _select_volume_baseline(rows) == (1_000_000 + 1_100_000 + 1_050_000) / 3

    def test_falls_back_to_everything_when_too_few_daily_bars(self):
        rows = [(1_000_000, True), (50_000, False), (60_000, False)]
        # Only 1 daily bar (< 3) — not enough to be a meaningful baseline on
        # its own, so fall back to averaging everything available.
        assert _select_volume_baseline(rows) == (1_000_000 + 50_000 + 60_000) / 3

    def test_no_data_returns_zero(self):
        assert _select_volume_baseline([]) == 0.0

    def test_ignores_none_and_zero_volumes(self):
        rows = [(1_000_000, True), (1_100_000, True), (1_050_000, True), (0, False)]
        assert _select_volume_baseline(rows) == (1_000_000 + 1_100_000 + 1_050_000) / 3
