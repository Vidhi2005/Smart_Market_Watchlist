"""
Template-based fallback explanations — used when LLM is unavailable.
"""
from __future__ import annotations


def template_explanation(
    symbol: str,
    attention_level: str,
    stock_pct_change: float,
    bench_pct_change: float,
    volume_ratio: float,
    news_count_24h: int,
    breakout: float,
) -> str:
    """Returns a clean, fact-based explanation without LLM."""
    parts: list[str] = []

    direction = "up" if stock_pct_change >= 0 else "down"
    parts.append(
        f"{symbol} moved {direction} {abs(stock_pct_change):.1f}% "
        f"vs market {bench_pct_change:+.1f}%."
    )

    if volume_ratio >= 1.5:
        parts.append(f"Volume is {volume_ratio:.1f}x average.")

    if news_count_24h >= 3:
        parts.append(f"{news_count_24h} news articles in the last 24 hours.")
    elif news_count_24h > 0:
        parts.append(f"{news_count_24h} recent news article(s).")

    if breakout >= 0.9:
        parts.append("Near a 30-day extreme.")

    return " ".join(parts) or f"{symbol} showed notable activity ({attention_level.lower()})."


def hallucination_check(response: str, allowed_percentages: list[float]) -> bool:
    """
    Returns True if the response is safe (no invented percentages).
    Scans for any XX.X% pattern and checks against allowed values.
    """
    import re
    found = re.findall(r"[-+]?\d+\.?\d*%", response)
    # allowed_percentages are stored as magnitudes (abs of the real values);
    # a stock down -2.19% legitimately renders as "-2.19%" in the model's
    # prose, so compare magnitudes — not raw signed values — against them.
    allowed_magnitudes = [abs(a) for a in allowed_percentages]
    for f in found:
        pct_str = f.replace("%", "").replace("+", "")
        try:
            val = float(pct_str)
        except ValueError:
            return False  # Unparseable — reject
        # Allow ±0.5% tolerance
        if not any(abs(abs(val) - a) < 0.5 for a in allowed_magnitudes):
            return False
    return True
