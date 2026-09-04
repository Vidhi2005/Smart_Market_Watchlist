"""
Signal computation functions — pure, stateless, testable.

Each function takes raw market data and returns a normalized float in [0, 1].
Weights are applied later in scoring.py.
"""
from __future__ import annotations

import math
from decimal import Decimal


# ── 1. Price-move signal ─────────────────────────────────────────────────────

def price_move_signal(
    current_price: Decimal,
    previous_close: Decimal,
    typical_daily_move_pct: float = 1.5,
) -> float:
    """
    Measures how large today's move is relative to the stock's typical daily swing.
    Returns 0–1.
    """
    if previous_close <= 0:
        return 0.0
    pct = float(abs((current_price - previous_close) / previous_close) * 100)
    # Sigmoid-like saturation: score=1 when pct >= 3x typical move
    score = 1 - math.exp(-pct / typical_daily_move_pct)
    return min(1.0, max(0.0, score))


# ── 2. Volume-spike signal ───────────────────────────────────────────────────

def volume_spike_signal(
    current_volume: int,
    avg_volume: float,
) -> float:
    """
    Measures how unusual today's volume is vs the 30-day average.
    Returns 0–1.
    """
    if avg_volume <= 0 or current_volume <= 0:
        return 0.0
    ratio = current_volume / avg_volume
    # 1x = 0, 2x = ~0.63, 3x = ~0.86, 5x = ~0.98
    score = 1 - math.exp(-(ratio - 1))
    return min(1.0, max(0.0, score))


# ── 3. Relative-move signal (vs benchmark) ───────────────────────────────────

def relative_move_signal(
    stock_pct_change: float,
    benchmark_pct_change: float,
) -> float:
    """
    Measures how much the stock moved beyond the broad market.
    Returns 0–1.
    """
    relative = abs(stock_pct_change - benchmark_pct_change)
    # 2% excess = ~0.63, 5% = ~0.92, 10% = ~0.99
    score = 1 - math.exp(-relative / 2.0)
    return min(1.0, max(0.0, score))


# ── 4. Breakout signal ───────────────────────────────────────────────────────

def breakout_signal(
    current_price: Decimal,
    high_30d: Decimal,
    low_30d: Decimal,
) -> float:
    """
    Returns 1 if price breaches the 30-day high/low, 0 if fully within range.
    Partial score for proximity to extremes.
    """
    if high_30d <= low_30d:
        return 0.0
    rng = float(high_30d - low_30d)
    price = float(current_price)
    high = float(high_30d)
    low = float(low_30d)

    if price >= high:
        return 1.0
    if price <= low:
        return 1.0

    # How close is price to an extreme? Max score = 0.9 at 95% of range
    dist_to_high = (high - price) / rng
    dist_to_low = (price - low) / rng
    proximity = 1 - min(dist_to_high, dist_to_low)
    return min(0.9, max(0.0, proximity))


# ── 5. News-surge signal ─────────────────────────────────────────────────────

def news_surge_signal(
    news_count_24h: int,
    avg_daily_news: float = 2.0,
) -> float:
    """
    Returns a score based on unusual news volume in the last 24 hours.
    Returns 0–1.
    """
    if news_count_24h <= 0:
        return 0.0
    if avg_daily_news <= 0:
        avg_daily_news = 1.0
    ratio = news_count_24h / avg_daily_news
    score = 1 - math.exp(-(ratio - 1) / 1.5)
    return min(1.0, max(0.0, score))


# ── Pct-change helper ─────────────────────────────────────────────────────────

def pct_change(current: Decimal, previous: Decimal) -> float:
    """Simple percentage change, returns 0.0 on bad inputs."""
    if not previous or previous == 0:
        return 0.0
    return float((current - previous) / previous) * 100
