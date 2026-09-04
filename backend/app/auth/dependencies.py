"""
FastAPI dependency for extracting the authenticated user from a bearer token.
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import decode_access_token
from app.database import get_db
from app.models import User

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _UNAUTHORIZED

    token = authorization.split(" ", 1)[1].strip()
    user_id = decode_access_token(token)
    if not user_id:
        raise _UNAUTHORIZED

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise _UNAUTHORIZED

    return user
