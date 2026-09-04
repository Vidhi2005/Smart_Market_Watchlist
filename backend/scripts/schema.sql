-- ─────────────────────────────────────────────────────────────────────────────
-- Smart Market Watchlist — Database Schema
-- ─────────────────────────────────────────────────────────────────────────────

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── users ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) UNIQUE NOT NULL,
    display_name  VARCHAR(100) NOT NULL,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);
-- Migration: real auth. Nullable so pre-existing rows don't break; app layer
-- requires it for anyone authenticating.
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);
-- Migration: country/timezone, captured at signup, drives timezone-correct
-- UI (e.g. the dashboard greeting) instead of guessing from server clock.
ALTER TABLE users ADD COLUMN IF NOT EXISTS country VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) NOT NULL DEFAULT 'UTC';

-- ── symbols ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS symbols (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol        VARCHAR(20)  UNIQUE NOT NULL,
    company_name  VARCHAR(255) NOT NULL,
    sector        VARCHAR(100),
    exchange      VARCHAR(50)
);

-- ── watchlists ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS watchlists (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name       VARCHAR(100) NOT NULL DEFAULT 'My Watchlist',
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_watchlists_user_id ON watchlists(user_id);

-- ── watchlist_items ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS watchlist_items (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    watchlist_id UUID        NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    symbol_id    UUID        NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    added_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(watchlist_id, symbol_id)
);
CREATE INDEX IF NOT EXISTS idx_watchlist_items_watchlist ON watchlist_items(watchlist_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_items_symbol   ON watchlist_items(symbol_id);

-- ── market_snapshots ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS market_snapshots (
    id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol_id          UUID        NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    price              NUMERIC(18,4) NOT NULL,
    volume             BIGINT,
    previous_close     NUMERIC(18,4),
    open               NUMERIC(18,4),
    high               NUMERIC(18,4),
    low                NUMERIC(18,4),
    source             VARCHAR(50)  NOT NULL DEFAULT 'finnhub',
    provider_timestamp TIMESTAMPTZ,
    ingested_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    quality_status     VARCHAR(20)  NOT NULL DEFAULT 'FRESH'  -- FRESH | STALE
);
CREATE INDEX IF NOT EXISTS idx_snapshots_symbol_time ON market_snapshots(symbol_id, ingested_at DESC);

-- ── news_events ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS news_events (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol_id    UUID        NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    headline     TEXT        NOT NULL,
    summary      TEXT,
    source       VARCHAR(100),
    url          TEXT,
    published_at TIMESTAMPTZ NOT NULL,
    ingested_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    dedup_hash   VARCHAR(64) UNIQUE NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_news_symbol_time ON news_events(symbol_id, published_at DESC);

-- ── market_events ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS market_events (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol_id   UUID        NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    snapshot_id UUID        REFERENCES market_snapshots(id) ON DELETE SET NULL,
    event_type  VARCHAR(50) NOT NULL,  -- PRICE_MOVE | VOLUME_SPIKE | BREAKOUT | NEWS_SURGE | RELATIVE_MOVE
    magnitude   NUMERIC(10,4),
    signals     JSONB       NOT NULL DEFAULT '{}',
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_events_symbol_time ON market_events(symbol_id, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_signals     ON market_events USING gin(signals);

-- ── user_observations ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_observations (
    user_id                   UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol_id                 UUID        NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    last_observed_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_observed_snapshot_id UUID        REFERENCES market_snapshots(id) ON DELETE SET NULL,
    PRIMARY KEY (user_id, symbol_id)
);

-- ── user_attention ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_attention (
    id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_id           UUID        NOT NULL REFERENCES market_events(id) ON DELETE CASCADE,
    score              NUMERIC(6,4) NOT NULL,
    confidence         NUMERIC(6,4) NOT NULL DEFAULT 1.0,
    attention_level    VARCHAR(20)  NOT NULL,  -- CRITICAL | HIGH | WATCH | NO_CHANGE
    explanation        TEXT,
    explanation_source VARCHAR(20)  NOT NULL DEFAULT 'template',  -- llm | template
    computed_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE(user_id, event_id)
);
CREATE INDEX IF NOT EXISTS idx_attention_user_score ON user_attention(user_id, score DESC);
