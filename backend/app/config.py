"""
Application settings — loaded from environment / .env file.
"""
from typing import Literal, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Values that must never be treated as a real production JWT secret — the
# class-level dev default, and the placeholder that ships in .env.example
# (which is also, today, what the real .env file on disk still contains).
_INSECURE_JWT_SECRETS = {
    "dev-insecure-secret-change-me",
    "change-this-to-a-long-random-string-in-production",
    "",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Environment ───────────────────────────────────────────────────────────
    environment: Literal["development", "production"] = "development"

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://smartwatchlist:smartwatchlist"
        "@localhost:5432/smart_market_watchlist"
    )

    @field_validator("database_url", mode="after")
    @classmethod
    def _normalize_database_url(cls, v: str) -> str:
        """
        Hosting platforms (Render, Heroku, Railway) commonly hand out a
        plain postgresql:// or postgres:// connection string — this app's
        engine is async and requires the asyncpg driver be named explicitly
        in the URL scheme, or create_async_engine() raises immediately at
        import time. Normalize rather than require every deploy target to
        know this app-specific detail.
        """
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            v = "postgresql+asyncpg://" + v[len("postgresql://"):]
        return v

    # ── Market Data ───────────────────────────────────────────────────────────
    finnhub_api_key: str = ""
    benchmark_symbol: str = "SPY"
    # Optional secondary providers — empty key means "not configured," and a
    # provider absent from its market's chain below is simply never called
    # regardless of whether a key exists for it (having a key only makes a
    # provider *available*, never automatically active — see ingestion_service).
    alpha_vantage_api_key: str = ""
    twelve_data_api_key: str = ""
    # Comma-separated provider names, tried in order. Twelve Data is verified
    # (live-tested) to return real US quotes on a workable free-tier budget
    # (800/day, 8/min) — added as a real secondary. Alpha Vantage's free tier
    # is 25 requests/day total, live-confirmed — nowhere near enough to sit in
    # an active polling fallback path, so it's built and testable but not
    # wired into either chain. Twelve Data's NSE/BSE data is live-confirmed to
    # be paywalled on the free tier ("available starting with the Grow or
    # Venture plan"), so it is NOT in the India chain — yfinance stays India's
    # only provider.
    us_provider_chain: str = "finnhub,twelve_data,yfinance"
    india_provider_chain: str = "yfinance"

    # ── LLM ───────────────────────────────────────────────────────────────────
    gemini_api_key: str = ""

    # ── Auth ──────────────────────────────────────────────────────────────────
    # Dev-only fallback secret — set JWT_SECRET_KEY in .env for real deployments.
    # Enforced non-placeholder/non-empty/>=32 chars when environment=production
    # (see _validate_production_secrets below) — this default only ever
    # applies in development.
    jwt_secret_key: str = "dev-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Comma-separated emails allowed to hit genuinely administrative,
    # expensive, global endpoints (currently just /api/admin/trigger-poll).
    # Empty by default — nobody is admin until explicitly configured, in
    # dev or prod alike.
    admin_emails: str = ""

    # ── CORS ──────────────────────────────────────────────────────────────────
    # http://localhost:3000 is always allowed (local dev). Production adds
    # this exact origin — no wildcard support (Starlette's CORSMiddleware
    # only does exact string match).
    frontend_origin: Optional[str] = None

    # ── Demo Mode ─────────────────────────────────────────────────────────────
    demo_mode_enabled: bool = True

    # ── API Docs ──────────────────────────────────────────────────────────────
    docs_enabled: bool = True

    # ── Request limits ────────────────────────────────────────────────────────
    max_body_size_bytes: int = 1_000_000

    # ── Gemini ────────────────────────────────────────────────────────────────
    gemini_timeout_seconds: float = 8.0

    # ── Rate limiting (in-memory, single-process — see README/report caveat) ──
    rate_limit_login_max: int = 5
    rate_limit_login_window_seconds: int = 60
    rate_limit_signup_max: int = 3
    rate_limit_signup_window_seconds: int = 60
    rate_limit_search_max: int = 30
    rate_limit_search_window_seconds: int = 60
    rate_limit_add_symbol_max: int = 10
    rate_limit_add_symbol_window_seconds: int = 60
    rate_limit_demo_max: int = 1
    rate_limit_demo_window_seconds: int = 20

    # ── App Behaviour ─────────────────────────────────────────────────────────
    # 45s keeps real headroom under Finnhub's free-tier ~60 req/min ceiling (the
    # poll loop already sleeps 1s/symbol) while feeling "live" on the frontend.
    poll_interval_seconds: int = 45
    log_level: str = "INFO"

    # ── Demo User ─────────────────────────────────────────────────────────────
    demo_user_id: str = "00000000-0000-0000-0000-000000000001"

    # ── Scoring Thresholds ────────────────────────────────────────────────────
    # Raw signal weights
    weight_price_move: float = 0.35
    weight_volume_spike: float = 0.20
    weight_relative_move: float = 0.25
    weight_breakout: float = 0.10
    weight_news_surge: float = 0.10

    # Attention level score cutoffs
    critical_threshold: float = 0.70
    high_threshold: float = 0.40
    watch_threshold: float = 0.15

    # Minimum magnitude to create a market event
    event_floor: float = 0.005          # 0.5% price move

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        """
        Fail fast at process startup — not on the first request — if
        ENVIRONMENT=production would otherwise silently run with a
        forgeable JWT secret. Runs at Settings() construction time, which
        happens at import time (see `settings = Settings()` below), so a
        misconfigured production deploy never binds a port.

        FINNHUB_API_KEY/GEMINI_API_KEY are deliberately NOT enforced here:
        both already degrade gracefully by design (provider chain skip /
        template fallback), so hard-failing on either would change actual
        product behavior for a legitimate key-less deployment, which this
        hardening pass isn't meant to do.
        """
        if self.environment == "production":
            if (
                self.jwt_secret_key in _INSECURE_JWT_SECRETS
                or len(self.jwt_secret_key) < 32
            ):
                raise ValueError(
                    "JWT_SECRET_KEY is missing, a known placeholder, or "
                    "shorter than 32 characters while ENVIRONMENT=production. "
                    "Set a real, random secret (e.g. `openssl rand -hex 32`) "
                    "before starting the app."
                )
        return self


settings = Settings()

if settings.environment == "production":
    import logging as _logging

    _logger = _logging.getLogger(__name__)
    if not settings.finnhub_api_key:
        _logger.warning(
            "FINNHUB_API_KEY is not set in production — the US provider "
            "chain will skip straight to its next configured provider."
        )
    if not settings.gemini_api_key:
        _logger.warning(
            "GEMINI_API_KEY is not set in production — every explanation "
            "will use the deterministic template fallback."
        )
