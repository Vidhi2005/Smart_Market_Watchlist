"""
Application settings — loaded from environment / .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://smartwatchlist:smartwatchlist"
        "@localhost:5432/smart_market_watchlist"
    )

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
    jwt_secret_key: str = "dev-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

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


settings = Settings()
