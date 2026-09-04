"""
Gemini LLM client — wraps google-genai SDK with graceful fallback.
"""
from __future__ import annotations

import logging

from app.config import settings

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None and settings.gemini_api_key:
        try:
            from google import genai
            _client = genai.Client(api_key=settings.gemini_api_key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not initialize Gemini client: %s", exc)
    return _client


async def generate_explanation(prompt: str) -> str | None:
    """
    Call Gemini and return the text response.
    Returns None on any failure (caller falls back to template).
    """
    client = _get_client()
    if not client:
        return None
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            ),
        )
        text = response.text.strip()
        return text if text else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gemini call failed: %s", exc)
        return None
