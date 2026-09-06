"""
Admin gating for genuinely administrative, expensive, global endpoints.

No DB migration/role column — a comma-separated ADMIN_EMAILS env var checked
against the already-loaded authenticated user's email. Empty by default, so
nobody passes this check until it's explicitly configured.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.config import settings
from app.models import User


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    admin_emails = {
        e.strip().lower() for e in settings.admin_emails.split(",") if e.strip()
    }
    if current_user.email.lower() not in admin_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user
