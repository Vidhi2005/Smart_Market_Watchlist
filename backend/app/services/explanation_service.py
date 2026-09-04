"""
Explanation service — orchestrates LLM + fallback + hallucination check,
and caches results in user_attention table.
"""
from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.client import generate_explanation
from app.llm.fallback import hallucination_check, template_explanation
from app.llm.prompts import build_explanation_prompt
from app.models import MarketEvent, Symbol, UserAttention
from app.engine.scoring import RawSignals, score

logger = logging.getLogger(__name__)


async def get_or_generate_explanation(
    db: AsyncSession,
    event: MarketEvent,
    symbol: Symbol,
    user_id: str,
    avg_volume: float,
    news_count_24h: int,
) -> UserAttention:
    """
    Returns a cached UserAttention record, or generates + caches a new one.
    """
    # Check cache first
    cached = await db.execute(
        select(UserAttention).where(
            UserAttention.user_id == user_id,
            UserAttention.event_id == event.id,
        )
    )
    existing = cached.scalar_one_or_none()
    if existing:
        return existing

    sigs = event.signals
    stock_pct = float(sigs.get("stock_pct_change", 0))
    bench_pct = float(sigs.get("bench_pct_change", 0))
    final_score = float(sigs.get("final_score", 0))
    confidence = float(sigs.get("confidence", 1))
    attention_level = sigs.get("attention_level", "WATCH")

    volume_ratio = (
        float(sigs.get("volume_spike", 0)) * 3 + 1
    )  # approximate back-conversion

    # Try LLM
    explanation = None
    source = "template"
    from app.models import MarketSnapshot
    snap = None
    if event.snapshot_id:
        snap_result = await db.execute(
            select(MarketSnapshot).where(MarketSnapshot.id == event.snapshot_id)
        )
        snap = snap_result.scalar_one_or_none()

    current_price = float(snap.price) if snap else 0.0

    prompt = build_explanation_prompt(
        symbol=symbol.symbol,
        company_name=symbol.company_name,
        attention_level=attention_level,
        stock_pct_change=stock_pct,
        bench_pct_change=bench_pct,
        volume_ratio=volume_ratio,
        news_count_24h=news_count_24h,
        breakout=float(sigs.get("breakout", 0)),
        current_price=current_price,
        event_type=event.event_type,
    )

    llm_text = await generate_explanation(prompt)
    allowed = [abs(stock_pct), abs(bench_pct), volume_ratio, float(news_count_24h)]

    if llm_text and hallucination_check(llm_text, allowed):
        explanation = llm_text
        source = "llm"
    else:
        if llm_text:
            logger.warning("LLM output failed hallucination check for %s — using template", symbol.symbol)
        explanation = template_explanation(
            symbol=symbol.symbol,
            attention_level=attention_level,
            stock_pct_change=stock_pct,
            bench_pct_change=bench_pct,
            volume_ratio=volume_ratio,
            news_count_24h=news_count_24h,
            breakout=float(sigs.get("breakout", 0)),
        )

    ua = UserAttention(
        user_id=user_id,
        event_id=event.id,
        score=Decimal(str(round(final_score, 4))),
        confidence=Decimal(str(round(confidence, 4))),
        attention_level=attention_level,
        explanation=explanation,
        explanation_source=source,
    )
    db.add(ua)
    await db.flush()
    return ua
