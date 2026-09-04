"""
Simple market-hours calendar — US Eastern Time.
Uses python-dateutil for timezone handling (stdlib only).
"""
from __future__ import annotations

from datetime import date, datetime, time, timezone
import zoneinfo

# US market holidays 2025-2026 (static list — good enough for demo)
_US_HOLIDAYS: set[date] = {
    date(2025, 1, 1),   # New Year's Day
    date(2025, 1, 20),  # MLK Day
    date(2025, 2, 17),  # Presidents' Day
    date(2025, 4, 18),  # Good Friday
    date(2025, 5, 26),  # Memorial Day
    date(2025, 6, 19),  # Juneteenth
    date(2025, 7, 4),   # Independence Day
    date(2025, 9, 1),   # Labor Day
    date(2025, 11, 27), # Thanksgiving
    date(2025, 12, 25), # Christmas
    date(2026, 1, 1),
    date(2026, 1, 19),
    date(2026, 2, 16),
    date(2026, 4, 3),
    date(2026, 5, 25),
    date(2026, 6, 19),
    date(2026, 7, 3),
    date(2026, 9, 7),
    date(2026, 11, 26),
    date(2026, 12, 25),
}

_ET = zoneinfo.ZoneInfo("America/New_York")
_MARKET_OPEN  = time(9, 30)
_MARKET_CLOSE = time(16, 0)


def is_market_open(dt: datetime | None = None) -> bool:
    """Return True if the US equity market is currently open."""
    now = (dt or datetime.now(tz=timezone.utc)).astimezone(_ET)
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    if now.date() in _US_HOLIDAYS:
        return False
    return _MARKET_OPEN <= now.time() < _MARKET_CLOSE


_IST = zoneinfo.ZoneInfo("Asia/Kolkata")
_NSE_OPEN  = time(9, 15)
_NSE_CLOSE = time(15, 30)

# Indian market holidays 2025-2026
_NSE_HOLIDAYS: set[date] = {
    date(2025, 1, 26),  # Republic Day
    date(2025, 3, 14),  # Holi
    date(2025, 3, 31),  # Id-Ul-Fitr
    date(2025, 4, 18),  # Good Friday
    date(2025, 5, 1),   # Maharashtra Day
    date(2025, 8, 15),  # Independence Day
    date(2025, 10, 2),  # Mahatma Gandhi Jayanti
    date(2025, 10, 21), # Diwali
    date(2025, 12, 25), # Christmas
    date(2026, 1, 26),
    date(2026, 3, 20),
    date(2026, 4, 3),
    date(2026, 4, 14),
    date(2026, 5, 1),
    date(2026, 8, 15),
    date(2026, 10, 2),
    date(2026, 11, 8),
    date(2026, 12, 25),
}


def is_indian_market_open(dt: datetime | None = None) -> bool:
    """Return True if the Indian equity market (NSE/BSE) is currently open."""
    now = (dt or datetime.now(tz=timezone.utc)).astimezone(_IST)
    if now.weekday() >= 5:  # Saturday or Sunday
        return False
    if now.date() in _NSE_HOLIDAYS:
        return False
    return _NSE_OPEN <= now.time() < _NSE_CLOSE


def next_open_seconds() -> float:
    """Seconds until the next market open (for scheduling)."""
    now = datetime.now(tz=_ET)
    candidate = now.replace(hour=9, minute=30, second=0, microsecond=0)
    if now.time() >= _MARKET_CLOSE or now.weekday() >= 5:
        candidate = candidate.replace(day=candidate.day + 1)
    return max(0.0, (candidate - now).total_seconds())

