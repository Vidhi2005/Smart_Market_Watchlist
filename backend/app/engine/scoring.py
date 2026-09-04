"""
Scoring engine — combines raw signals into a final attention score.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


@dataclass
class RawSignals:
    price_move: float = 0.0
    volume_spike: float = 0.0
    relative_move: float = 0.0
    breakout: float = 0.0
    news_surge: float = 0.0


@dataclass
class ScoredResult:
    raw_score: float
    corroboration_boost: float
    final_score: float
    confidence: float
    attention_level: str           # CRITICAL | HIGH | WATCH | NO_CHANGE
    signals: RawSignals


def _count_active_signals(s: RawSignals, threshold: float = 0.2) -> int:
    return sum(
        1
        for v in [s.price_move, s.volume_spike, s.relative_move, s.breakout, s.news_surge]
        if v >= threshold
    )


def compute_raw_score(s: RawSignals) -> float:
    """Weighted sum of normalized signals."""
    return (
        s.price_move    * settings.weight_price_move
        + s.volume_spike  * settings.weight_volume_spike
        + s.relative_move * settings.weight_relative_move
        + s.breakout      * settings.weight_breakout
        + s.news_surge    * settings.weight_news_surge
    )


def corroboration_boost(raw: float, active_signals: int) -> float:
    """
    If multiple independent signals fire, boost the score.
    2 signals → +5%, 3 → +10%, 4+ → +15%.
    """
    if active_signals >= 4:
        return raw * 0.15
    if active_signals >= 3:
        return raw * 0.10
    if active_signals >= 2:
        return raw * 0.05
    return 0.0


def compute_confidence(s: RawSignals, data_is_fresh: bool) -> float:
    """
    Confidence reflects data quality and signal diversity.
    Stale data caps confidence at 0.6.
    """
    active = _count_active_signals(s)
    base = min(1.0, 0.4 + active * 0.15)
    if not data_is_fresh:
        base = min(base, 0.6)
    return round(base, 4)


def score(signals: RawSignals, data_is_fresh: bool = True) -> ScoredResult:
    """Main entry point — returns a fully scored result."""
    raw = compute_raw_score(signals)
    active = _count_active_signals(signals)
    boost = corroboration_boost(raw, active)
    final = min(1.0, raw + boost)
    conf = compute_confidence(signals, data_is_fresh)

    cfg = settings
    if final >= cfg.critical_threshold:
        level = "CRITICAL"
    elif final >= cfg.high_threshold:
        level = "HIGH"
    elif final >= cfg.watch_threshold:
        level = "WATCH"
    else:
        level = "NO_CHANGE"

    # Stale data hard-caps at WATCH
    if not data_is_fresh and level == "CRITICAL":
        level = "HIGH"

    return ScoredResult(
        raw_score=round(raw, 4),
        corroboration_boost=round(boost, 4),
        final_score=round(final, 4),
        confidence=conf,
        attention_level=level,
        signals=signals,
    )
