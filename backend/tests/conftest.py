"""
pytest configuration and shared fixtures.
"""
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.auth.security import create_access_token, hash_password
from app.database import get_db
from app.main import app
from app.models import User, Watchlist


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _reset_rate_limit_state():
    """The in-memory rate limiter is a module-level global by design (see
    app/utils/rate_limit.py) — reset it between tests so one test's calls
    don't count against another's limit."""
    from app.utils.rate_limit import _hits

    _hits.clear()
    yield
    _hits.clear()


# Defaults to the same dev Postgres the app already uses (Postgres-specific
# types — JSONB, native UUID — are used throughout models.py, so a SQLite
# swap would silently diverge from real behavior). Override with
# TEST_DATABASE_URL if isolation from local dev data is wanted. Each test
# runs inside a real transaction that's rolled back afterward, so nothing
# written during a test persists either way.
_TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://smartwatchlist:smartwatchlist@localhost:5433/smart_market_watchlist",
)
# NullPool: a pooled connection reused across pytest-asyncio's per-test event
# loops surfaced asyncpg "another operation is in progress" errors — a fresh,
# non-pooled connection per test avoids that entirely.
_engine = create_async_engine(_TEST_DATABASE_URL, poolclass=NullPool)


@pytest_asyncio.fixture
async def db_session():
    """
    One real transaction per test, rolled back at the end — including when
    code under test calls session.commit() itself (several services here
    do). join_transaction_mode="create_savepoint" is SQLAlchemy's built-in
    support for exactly this: the session runs inside a SAVEPOINT nested in
    our outer transaction, and an inner session.commit() only ends the
    savepoint (which SQLAlchemy transparently restarts), never the outer
    transaction — so the final rollback always discards everything.
    """
    async with _engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(
            bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def two_users(db_session):
    """Two distinct users, each with their own watchlist, plus minted
    tokens — created directly via the ORM so tests don't need a signup
    HTTP round trip just to set up fixtures."""
    user_a = User(email="idor-test-a@example.com", display_name="A", password_hash=hash_password("pw"))
    user_b = User(email="idor-test-b@example.com", display_name="B", password_hash=hash_password("pw"))
    db_session.add_all([user_a, user_b])
    await db_session.flush()

    wl_a = Watchlist(user_id=user_a.id, name="A's list")
    wl_b = Watchlist(user_id=user_b.id, name="B's list")
    db_session.add_all([wl_a, wl_b])
    await db_session.flush()

    return {
        "a": {"user": user_a, "watchlist": wl_a, "token": create_access_token(user_a.id)},
        "b": {"user": user_b, "watchlist": wl_b, "token": create_access_token(user_b.id)},
    }
