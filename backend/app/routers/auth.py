"""
Auth router — signup, login, current-user.
"""
from __future__ import annotations

import zoneinfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, SignupRequest, TokenResponse, UpdateProfileRequest, UserOut
from app.schemas import WatchlistCreate
from app.services import watchlist_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _valid_timezone(tz: str | None) -> str:
    """Falls back to UTC for anything not a real IANA zone — never trust
    client-supplied strings blindly, and never let a bad value crash the
    greeting formatter later."""
    if tz:
        try:
            zoneinfo.ZoneInfo(tz)
            return tz
        except Exception:  # noqa: BLE001
            pass
    return "UTC"


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)):
    email = payload.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="Invalid email")
    if len(payload.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    if not payload.display_name.strip():
        raise HTTPException(status_code=422, detail="Display name is required")

    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

    user = User(
        email=email,
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
        country=payload.country.strip() if payload.country else None,
        timezone=_valid_timezone(payload.timezone),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Every new user gets a default watchlist, same as the seeded demo user.
    await watchlist_service.create_watchlist(db, user.id, WatchlistCreate(name="My Watchlist"))

    token = create_access_token(user.id)
    return TokenResponse(token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    email = payload.email.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    token = create_access_token(user.id)
    return TokenResponse(token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)


@router.patch("/me", response_model=UserOut)
async def update_me(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.display_name is not None:
        name = payload.display_name.strip()
        if not name:
            raise HTTPException(status_code=422, detail="Display name is required")
        current_user.display_name = name

    if payload.country is not None:
        current_user.country = payload.country.strip() or None

    if payload.timezone is not None:
        current_user.timezone = _valid_timezone(payload.timezone)

    await db.commit()
    await db.refresh(current_user)
    return UserOut.model_validate(current_user)
