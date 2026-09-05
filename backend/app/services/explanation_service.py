"""
Explanation service — orchestrates LLM + fallback + hallucination check.

Deliberately a pure function with no DB access and no per-user concept: the
explanation for a market event depends only on that event's own signals
(symbol, price move, volume, news), never on which user is asking. Calling
this from ingestion (once, when the event is created) rather than from a
user's read request means:

  1. No LLM call is ever possible inside a GET /changes request — it's
     already been generated and stored on the MarketEvent by the time any
     user's request reads it.
  2. It's generated exactly once per event, not once per user who happens
     to view it first — 10,000 users watching NVDA share one explanation,
     not 10,000 independent Gemini calls for the same move.

(This replaces an earlier version that cached per (user_id, event_id) in a
user_attention table — a bug, not a feature: nothing in the cached row
actually varied by user, so the per-user keying only bought redundant LLM
calls and, worse, made the read path able to block on Gemini.)
"""
from __future__ import annotations

import logging

from app.llm.client import generate_explanation
from app.llm.fallback import hallucination_check, template_explanation

logger = logging.getLogger(__name__)


async def generate_event_explanation(
    *,
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
) -> tuple[str, str]:
    """Returns (explanation_text, source) where source is 'llm' or 'template'."""
    from app.llm.prompts import build_explanation_prompt

    prompt = build_explanation_prompt(
        symbol=symbol,
        company_name=company_name,
        attention_level=attention_level,
        stock_pct_change=stock_pct_change,
        bench_pct_change=bench_pct_change,
        volume_ratio=volume_ratio,
        news_count_24h=news_count_24h,
        breakout=breakout,
        current_price=current_price,
        event_type=event_type,
    )

    llm_text = await generate_explanation(prompt)
    allowed = [abs(stock_pct_change), abs(bench_pct_change), volume_ratio, float(news_count_24h)]

    if llm_text and hallucination_check(llm_text, allowed):
        return llm_text, "llm"

    if llm_text:
        logger.warning("LLM output failed hallucination check for %s — using template", symbol)

    template = template_explanation(
        symbol=symbol,
        attention_level=attention_level,
        stock_pct_change=stock_pct_change,
        bench_pct_change=bench_pct_change,
        volume_ratio=volume_ratio,
        news_count_24h=news_count_24h,
        breakout=breakout,
    )
    return template, "template"
