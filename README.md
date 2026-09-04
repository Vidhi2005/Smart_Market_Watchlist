# Smart Market Watchlist

> **An attention engine for your stock watchlist** — ranks what changed while
> you were away, explains why it matters, and shows you the signals behind
> every alert. See [PITCH.md](PITCH.md) for the 100-word version.

Built for the "Smart Market Watchlist" brief: create/manage a watchlist,
view live market data, and return later to see what actually changed —
without the obvious version of that product.

---

## Architecture Overview

```
┌──────────────────────────────────┐
│    Next.js Frontend (port 3000)  │
│    React Query · 15-20s polling  │
└─────────────────┬─────────────────┘
                   │ HTTP/REST + JWT bearer
┌──────────────────▼─────────────────┐
│    FastAPI Backend (port 8000)     │
│    APScheduler · JWT auth          │
└──┬───────────┬───────────┬─────────┘
   │           │           │
   ▼           ▼           ▼
Finnhub      yfinance   PostgreSQL      Gemini
(US/global)  (NSE/BSE)     DB          LLM API
```

Two independent market-data providers are routed per-symbol by ticker
suffix (`.NS` / `.BO` → yfinance, everything else → Finnhub), so the app
genuinely tracks both US and Indian equities on their own market calendars,
not a single US-only clock.

### Key Design Decisions

| Decision | Rationale |
|---|---|
| **Lazy attention scoring** (on read) | Zero computation for inactive users |
| **Real per-user auth (JWT)** | "What changed since you checked" needs a real per-user baseline, not a shared demo fiction |
| **Changes vs. Quotes are separate endpoints** | "What changed" (scored, filtered) and "what's the current price" (every tracked stock, always) are different questions — the brief asks for both |
| **Dynamic ticker resolution** | Adding a company validates and resolves it live against the provider instead of only matching a pre-seeded catalog |
| **Poll gated on either market being open** | NSE hours barely overlap US hours — gating on US-only silently starves Indian symbols |
| **Template fallback for LLM** | Works without a Gemini key, and survives the LLM being rate-limited or briefly unavailable |
| **Hallucination guard** | Rejects LLM responses with invented percentages before showing them to a user |
| **Commit-after-render** | Baseline only advances after the user has actually seen the change; a crashed tab sees it again |
| **Polling vs WebSockets** | Product is "return and see what changed," not a live trading ticker — polling matches that; tuned for a livelier feel without adding infrastructure |

### Scoring Weight Calibration

| Signal | Weight | Rationale |
|---|---|---|
| Price Move | 35% | Strongest "something happened" signal |
| Relative Move | 25% | Distinguishes stock-specific vs market-wide |
| Volume Spike | 20% | Confirms interest and conviction |
| News Surge | 10% | Corroborating catalyst |
| Breakout | 10% | Technical structure signal |

**Corroboration Boost**: 2 signals → +5%, 3 → +10%, 4+ → +15%

**Attention Levels**: CRITICAL (≥0.70) · HIGH (≥0.40) · WATCH (≥0.15) · NO_CHANGE

---

## Quick Start

### Prerequisites
- Docker Desktop
- Python 3.9+ (a `.venv` is expected at `backend/.venv`)
- Node.js 18+
- Finnhub API key (free tier at [finnhub.io](https://finnhub.io))
- Gemini API key (optional — template fallback works without it)

### 1. Start the database
```bash
docker compose up -d
```

### 2. Configure backend
```bash
cd backend
cp .env.example .env
# Edit .env: FINNHUB_API_KEY, optionally GEMINI_API_KEY, and set
# JWT_SECRET_KEY to a real random string (a dev fallback exists, but
# don't rely on it beyond local testing).
```

### 3. Install and seed
```bash
python -m venv .venv
.venv/Scripts/activate   # .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
python scripts/seed.py
# Idempotent — safe to re-run after a schema change. Seeds ~20 US +
# Indian symbols and a demo account: demo@smartwatchlist.dev / demo12345
```

### 4. Run the backend
```bash
uvicorn app.main:app --reload
# API docs: http://localhost:8000/docs
```

### 5. Run the frontend
```bash
cd ../frontend
cp .env.local.example .env.local
npm install
npm run dev
# Open: http://localhost:3000 — sign up, or log in with the demo account above
```

---

## Project Structure

```
backend/
  app/
    config.py              # Pydantic Settings (env vars)
    database.py             # SQLAlchemy async engine
    models.py                # ORM models
    schemas.py                 # Pydantic request/response schemas
    main.py                     # FastAPI app + lifespan (starts scheduler)
    auth/
      security.py            # bcrypt hashing, JWT issue/verify
      dependencies.py        # get_current_user FastAPI dependency
    engine/
      signals.py             # 5 pure signal functions
      scoring.py              # Weighted score + attention levels
      market_calendar.py       # US (ET) + Indian (IST) market hours
    providers/
      base.py                 # Abstract provider interface
      finnhub_provider.py      # US/global — quotes, candles, news, profile
      yfinance_provider.py     # NSE/BSE — same interface, no API key needed
    services/
      ingestion_service.py    # Poll + change detection + provider routing
      attention_service.py     # Core "what changed?" pipeline
      explanation_service.py    # LLM + fallback + hallucination guard
      observation_service.py    # Per-user baseline management
      watchlist_service.py       # CRUD + live ticker resolution
    routers/
      auth.py, health.py, watchlists.py, dashboard.py
    llm/
      client.py, prompts.py, fallback.py
    scheduler/jobs.py         # APScheduler — polls whenever either market is open
  scripts/
    schema.sql, seed.py, pull_live_data.py   # one-shot manual data pull
  tests/
    test_signals.py, test_scoring.py, test_fallback.py, conftest.py

frontend/
  src/
    app/
      page.tsx                     # Dashboard (Overview)
      login/, signup/               # Auth pages
      watchlists/, settings/         # Watchlist management, profile/system status
      stocks/[symbol]/page.tsx        # Stock detail + real price chart
    components/                       # AttentionCard, MarketOverview, Sidebar, etc.
    context/AuthContext.tsx            # Token + user state
    hooks/                              # React Query hooks (useChanges, useQuotes, useCandles, ...)
    lib/                                 # api.ts, types.ts, countries.ts, auth-storage.ts
```

---

## Running Tests
```bash
cd backend
pytest -v
```

---

## API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/signup` | — | Create account (+ default watchlist) |
| POST | `/api/auth/login` | — | Returns a JWT |
| GET | `/api/auth/me` | ✓ | Current user |
| PATCH | `/api/auth/me` | ✓ | Update display name / country / timezone |
| GET | `/api/health` | — | Health check (DB connectivity) |
| GET | `/api/watchlists` | ✓ | List the user's watchlists |
| POST | `/api/watchlists` | ✓ | Create a watchlist |
| GET | `/api/watchlists/{id}/changes` | ✓ | **What changed** — ranked, scored attention items |
| GET | `/api/watchlists/{id}/quotes` | ✓ | **Live price** for every tracked symbol, regardless of attention status |
| POST | `/api/watchlists/{id}/symbols` | ✓ | Add a symbol — resolves live if not already in the catalog |
| DELETE | `/api/watchlists/{id}/symbols/{sid}` | ✓ | Remove a symbol |
| GET | `/api/stocks/search?q=` | — | Search the local symbol catalog |
| GET | `/api/stocks/{symbol}/candles?range=1D\|1W\|1M` | — | Historical price points for charts |
| POST | `/api/observations/commit` | ✓ | Advance the user's "last checked" baseline |
| GET | `/api/dashboard` | ✓ | Per-user summary stats + market hours |
| POST | `/api/admin/trigger-poll` | — | Manually trigger a market data poll (demo utility) |

---

## Known Limitations

Deliberate scope cuts, not oversights:

- **Single watchlist per user in the UI** — the schema supports multiple watchlists per user; only the first is surfaced.
- **No WebSocket push** — polling was the chosen tradeoff for this product shape (see Key Design Decisions).
- **No password reset / email verification** — auth is real (bcrypt + JWT) but minimal.
- **US-market candle backfill can be capped by Finnhub's free tier** — `/stock/candle` sometimes 403s on the free plan; live quotes are unaffected, and yfinance-backed Indian symbols aren't subject to this.
