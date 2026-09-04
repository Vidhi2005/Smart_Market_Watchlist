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

    # ── LLM ───────────────────────────────────────────────────────────────────
    gemini_api_key: str = ""

    # ── App Behaviour ─────────────────────────────────────────────────────────
    poll_interval_seconds: int = 300
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
