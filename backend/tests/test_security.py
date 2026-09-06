"""
Security regression tests — authorization (IDOR), auth, rate limiting,
admin gating, input validation, CORS, and error-message hygiene.

Uses the `client`/`db_session`/`two_users` fixtures from conftest.py: a real
transactional Postgres session (rolled back after each test, including any
internal db.commit() the code under test makes) plus an httpx.AsyncClient
wired directly to the real FastAPI app via ASGITransport.
"""
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.database import get_db
from app.main import app
from app.models import User, UserObservation, WatchlistItem


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestAuthentication:
    async def test_unauthenticated_dashboard_returns_401(self, client):
        resp = await client.get("/api/dashboard")
        assert resp.status_code == 401


class TestObservationsCommitIDOR:
    """
    The core regression test: /api/observations/commit was the one
    endpoint in the app that accepted a watchlist_id without verifying it
    belonged to the caller. User A must not be able to touch User B's
    watchlist by supplying B's watchlist_id in the request body.
    """

    async def test_user_a_cannot_commit_against_user_b_watchlist(self, client, two_users, db_session):
        resp = await client.post(
            "/api/observations/commit",
            json={"watchlist_id": two_users["b"]["watchlist"].id},
            headers=_auth(two_users["a"]["token"]),
        )
        assert resp.status_code == 404

    async def test_idor_attempt_does_not_delete_victim_watchlist_items(self, client, two_users, db_session):
        # Give B a demo-flagged item — the exact row shape the pre-fix bug
        # could delete out of a watchlist the caller didn't own.
        from app.models import Symbol

        symbol = Symbol(symbol="IDORTEST", company_name="IDOR Test Co")
        db_session.add(symbol)
        await db_session.flush()

        item = WatchlistItem(
            watchlist_id=two_users["b"]["watchlist"].id,
            symbol_id=symbol.id,
            is_demo=True,
        )
        db_session.add(item)
        await db_session.flush()

        resp = await client.post(
            "/api/observations/commit",
            json={"watchlist_id": two_users["b"]["watchlist"].id},
            headers=_auth(two_users["a"]["token"]),
        )
        assert resp.status_code == 404

        still_there = await db_session.execute(
            select(WatchlistItem).where(WatchlistItem.id == item.id)
        )
        assert still_there.scalar_one_or_none() is not None


class TestWatchlistOwnership:
    """Regression guard for the endpoints that already enforced ownership
    correctly before this pass — confirms the pattern still holds."""

    async def test_get_watchlist_cross_user_is_404(self, client, two_users):
        resp = await client.get(
            f"/api/watchlists/{two_users['b']['watchlist'].id}",
            headers=_auth(two_users["a"]["token"]),
        )
        assert resp.status_code == 404


class TestRateLimiting:
    async def test_login_rate_limit_returns_429(self, client):
        from app.config import settings

        payload = {"email": "nobody@example.com", "password": "wrong-password"}
        last_status = None
        for _ in range(settings.rate_limit_login_max + 1):
            resp = await client.post("/api/auth/login", json=payload)
            last_status = resp.status_code
        assert last_status == 429

    async def test_normal_dashboard_polling_is_never_rate_limited(self, client, two_users):
        for _ in range(20):
            resp = await client.get("/api/dashboard", headers=_auth(two_users["a"]["token"]))
            assert resp.status_code == 200


class TestAdminGating:
    async def test_trigger_poll_forbidden_for_non_admin(self, client, two_users):
        with patch("app.config.settings.admin_emails", ""):
            resp = await client.post(
                "/api/admin/trigger-poll", headers=_auth(two_users["a"]["token"])
            )
        assert resp.status_code == 403

    async def test_trigger_poll_allowed_for_configured_admin(self, client, two_users):
        admin_email = two_users["a"]["user"].email
        with patch("app.config.settings.admin_emails", admin_email), \
             patch("app.services.ingestion_service.poll_market_data", return_value=None), \
             patch("app.services.ingestion_service.poll_news", return_value=None):
            resp = await client.post(
                "/api/admin/trigger-poll", headers=_auth(two_users["a"]["token"])
            )
        assert resp.status_code == 200


class TestDemoScenarioGuards:
    async def test_demo_scenario_second_rapid_call_is_rate_limited(self, client, two_users):
        # Avoid a real Gemini call from this test — force the deterministic
        # template fallback path.
        with patch("app.llm.client.generate_explanation", return_value=None):
            first = await client.post(
                f"/api/admin/demo-scenario?watchlist_id={two_users['a']['watchlist'].id}",
                headers=_auth(two_users["a"]["token"]),
            )
            second = await client.post(
                f"/api/admin/demo-scenario?watchlist_id={two_users['a']['watchlist'].id}",
                headers=_auth(two_users["a"]["token"]),
            )
        assert first.status_code == 200
        assert second.status_code == 429

    async def test_demo_scenario_disabled_returns_404(self, client, two_users):
        with patch("app.config.settings.demo_mode_enabled", False):
            resp = await client.post(
                f"/api/admin/demo-scenario?watchlist_id={two_users['a']['watchlist'].id}",
                headers=_auth(two_users["a"]["token"]),
            )
        assert resp.status_code == 404


class TestInputValidation:
    async def test_oversized_signup_display_name_is_422_not_500(self, client):
        resp = await client.post(
            "/api/auth/signup",
            json={
                "email": "toolong@example.com",
                "password": "password123",
                "display_name": "x" * 500,
            },
        )
        assert resp.status_code == 422


class TestCORS:
    async def test_preflight_from_unlisted_origin_is_not_echoed(self, client):
        resp = await client.options(
            "/api/dashboard",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") != "https://evil.example"

    async def test_preflight_from_localhost_dev_origin_is_allowed(self, client):
        resp = await client.options(
            "/api/dashboard",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


class TestHealthEndpointErrorHygiene:
    async def test_db_failure_never_leaks_exception_text(self):
        class _BoomSession:
            async def execute(self, *args, **kwargs):
                raise RuntimeError("password authentication failed for user \"smartwatchlist\"")

        async def _override():
            yield _BoomSession()

        app.dependency_overrides[get_db] = _override
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/api/health")
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        assert "password authentication failed" not in str(body)
        assert body["db"] == "error"
