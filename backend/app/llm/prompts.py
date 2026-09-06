"""
Prompt templates for the explanation service.
"""
from __future__ import annotations


def build_explanation_prompt(
    symbol: str,
    company_name: str,
    attention_level: str,
    stock_pct_change: float,
    bench_pct_change: float,
    volume_ratio: float,
    news_count_24h: int,
    breakout: float,
    current_price: float,
    event_type: str,
) -> str:
    # Defensive truncation matching the Symbol table's own column limits
    # (String(20)/String(255)) — these values are provider-sourced, not
    # directly user-typed, but this keeps the prompt bounded regardless.
    symbol = symbol[:20]
    company_name = company_name[:255]

    return f"""You are a concise financial analyst writing a one-sentence explanation (max 35 words) for a retail investor's watchlist alert.

Stock: {symbol} ({company_name})
Alert Level: {attention_level}
Current Price: ${current_price:.2f}
Price Change Today: {stock_pct_change:+.2f}% (market moved {bench_pct_change:+.2f}%)
Volume vs Average: {volume_ratio:.1f}x normal
News Articles (24h): {news_count_24h}
Near 30-Day High/Low: {"Yes" if breakout > 0.5 else "No"}

Write ONE sentence (max 35 words) explaining why this stock needs attention. Do NOT use the word "I". Be specific about what changed. Only use percentages from the data above — do not invent numbers."""
