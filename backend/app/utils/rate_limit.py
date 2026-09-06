"""
Minimal in-memory rate limiter.

Single-process only, by design — mirrors the existing _last_trigger_at
in-memory cooldown pattern already used in routers/dashboard.py for
/api/admin/trigger-poll, generalized to per-key sliding windows so it can
also cover login/signup/search/add-symbol/demo-scenario.

This is correct and sufficient for the current single-instance deployment
(see the deployment constraint on running exactly one backend process,
which this app already requires because APScheduler also runs in-process).
It is NOT safe under horizontal scaling — each process gets its own
independent counters. Do not treat it as multi-instance-safe.
"""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone

from fastapi import HTTPException

_hits: dict[str, deque[datetime]] = defaultdict(deque)


def check_rate_limit(key: str, max_calls: int, window_seconds: int) -> None:
    """Raises HTTPException(429) if `key` has exceeded `max_calls` within
    the trailing `window_seconds`; otherwise records this call and returns."""
    now = datetime.now(tz=timezone.utc)
    dq = _hits[key]
    while dq and (now - dq[0]).total_seconds() > window_seconds:
        dq.popleft()
    if len(dq) >= max_calls:
        raise HTTPException(status_code=429, detail="Too many requests — please slow down.")
    dq.append(now)
