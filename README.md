# Smart Market Watchlist

> **An attention engine for your stock watchlist** — ranks what changed while
> you were away, explains why it matters, and shows you the signals behind
> every alert. See [PITCH.md](PITCH.md) for the 100-word version.

Built for the "Smart Market Watchlist" brief: create/manage a watchlist,
view live market data, and return later to see what actually changed —
without the obvious version of that product.

**Contents:** [Architecture](#architecture-overview) ·
[Global vs. user state](#global-market-state-vs-user-observation-state) ·
[Event lifecycle](#event-lifecycle) ·
[Provider resilience](#provider-resilience) ·
[Latency](#latency-no-external-calls-in-the-user-request-path) ·
[Design decisions](#key-design-decisions) ·
[Scoring](#scoring-weight-calibration) ·
[Demo Mode](#demo-mode) ·
[Quick Start](#quick-start) ·
[Project Structure](#project-structure) ·
[Tests](#running-tests) ·
[API Reference](#api-reference) ·
[Scaling](#scaling-reasoning) ·
[Known Limitations](#known-limitations)

---

## Architecture Overview

```
┌─────────────────────────────────────┐
│       Next.js Frontend (:3000)       │
│     React Query · 15–20s polling     │
└──────────────────┬────────────────────┘
                    │ HTTP/REST + JWT bearer
┌───────────────────▼────────────────────┐
│        FastAPI Backend (:8000)          │
│        APScheduler · JWT auth           │
└────┬─────────┬─────────┬─────────┬──────┘
     │         │         │         │
     ▼         ▼         ▼         ▼
  Finnhub   yfinance  PostgreSQL  Gemini
(US/global) (NSE/BSE)     DB     LLM API
```

Two independent market-data providers are routed per-symbol by ticker
suffix (`.NS` / `.BO` → yfinance, everything else → Finnhub), so the app
genuinely tracks both US and Indian equities on their own market calendars,
not a single US-only clock.

### Global market state vs. user observation state

This is the architectural principle the whole product rests on:

```
MARKET STATE IS GLOBAL.        (symbols, snapshots, events, news)
OBSERVATION STATE IS PER-USER.  (last_observed_at, last_observed_snapshot_id)
```

Ingestion, change detection, and `MarketEvent` creation never know or care
which user is looking — one poll of NVDA serves every user tracking it.
`attention_service` is where the two meet: it reads a user's own
`UserObservation.last_observed_snapshot_id` to compute **"since you
checked"** (`since_checked_change_pct` in `AttentionItem`), which is
distinct from `price_change_pct` (today's move vs. `previous_close` — real,
useful market context, just not the same question). Two users who added
NVDA at different times get different `since_checked_change_pct` values
from the exact same underlying `MarketEvent` — nothing is duplicated
per-user, only the baseline comparison is.

### Event lifecycle

A symbol sitting at HIGH for ten consecutive 45s polls does not create ten
`MarketEvent` rows. `engine/scoring.classify_transition` compares each new
score against the most recent prior event for that symbol and only creates
a new one on a real transition — `NEW` (first ever), `ESCALATION` /
`DEESCALATION` (crossed a level, or moved >0.10 within the same level), or
silently skips a `CONTINUING` state. The transition kind is stored in the
event's own `signals` JSONB for explanation context.

### Provider resilience

- **Retry**: each provider retries its own transient failures (timeout,
  429, 5xx) with exponential backoff before giving up.
- **Fallback**: if the primary provider still fails, non-Indian symbols
  fall back to yfinance (it covers global tickers, no API key required) —
  `ingestion_service.get_quote_with_fallback`. `.NS`/`.BO` symbols have no
  fallback (yfinance is already the only real source for NSE/BSE).
- **Conflict detection**: run once, at the point a new ticker is first
  resolved (`watchlist_service._resolve_new_symbol`) rather than on every
  poll — cross-checking both providers continuously would double the
  ongoing call volume against the very free-tier ceiling the poll interval
  is tuned around, for marginal benefit. A >2% disagreement between
  providers at resolution time is logged as a real, exercised conflict path.
- **Volume baseline semantics**: `MarketSnapshot.is_daily_bar` distinguishes
  real daily OHLCV rows (from `bootstrap_historical`) from live-poll rows.
  A "30-day average volume" is only computed from `is_daily_bar` rows when
  there are enough of them (`ingestion_service._select_volume_baseline`) —
  live polls can carry intraday-cumulative volume (yfinance) or no volume
  at all (Finnhub's `/quote` doesn't return one), neither comparable to a
  single day's figure on its own.

### Latency: no external calls in the user request path

In a stock product, "the dashboard is slow" is a trust problem, not a
cosmetic one. This was audited directly rather than assumed:

**The finding.** `GET /changes` could previously call Gemini synchronously.
The root cause wasn't a missing queue — it was a data-modeling bug: the
cached score/confidence/explanation for a market event was keyed by
`(user_id, event_id)`, even though *none of that content depends on which
user is asking* — it's a pure function of the event's own signals. The
practical effect: the first user to view a newly-flagged event paid an
inline Gemini call, and — worse — the *next* distinct user to view the
same event paid another one, independently, for an identical explanation
of an identical event. 10,000 users watching NVDA could mean up to 10,000
redundant LLM calls for one move, not one.

**The fix.** Explanation generation moved into `run_change_detection`
(background ingestion, already scheduler-driven) and is stored directly on
the `MarketEvent.signals` JSONB — once per event, ever. `attention_service
.get_changes()` is now a pure read: score, confidence, attention level, and
explanation all come straight off the event row. No LLM call, no external
provider call, and no per-user duplication is possible in the request path
— structurally, not by convention.

**Measured, not claimed.** `scripts/benchmark_changes.py` seeds real DB
rows (bypassing providers/LLM entirely, same as the demo scenario) and
times `get_changes()` directly for 5/20/50/100-symbol watchlists:

| Symbols | min (ms) | avg (ms) | max (ms) |
|---|---|---|---|
| 5   | 28.5 | 31.6 | 35.5 |
| 20  | 36.2 | 36.9 | 38.4 |
| 50  | 42.6 | 45.2 | 47.7 |
| 100 | 56.8 | 67.2 | 72.8 |

Reproducible across repeated runs (see the script's own inline warm-up
notes on SQLAlchemy/asyncpg statement caching, which otherwise inflates
whichever size runs first). Growth from 5→100 symbols (20x) is roughly
2x latency, not 20x — direct evidence the batched-query fix holds under
load, not just in the common case.

**Adaptive polling.** `useChanges`/`useQuotes` poll at 15s while a relevant
market is open, backed off to 2 minutes when both US and India are closed
(no new snapshot is coming outside trading hours). `refetchIntervalInBackground:
false` means a backgrounded tab doesn't poll at all — set explicitly in
`layout.tsx`'s `QueryClient` defaults even though it's also the library
default, so the intent reads clearly in the code.

**Index audit.** Checked every query path in `attention_service`,
`ingestion_service`, `observation_service`, and `watchlist_service` against
the existing schema. Result: no new indexes were needed —
`idx_events_symbol_time` and `idx_news_symbol_time` (both `(symbol_id,
timestamp DESC)`) already match the batched `IN (...)` query shapes the
N+1 fix introduced. Documenting "audited, found correct" rather than
adding indexes with no query to justify them.

**Operational visibility.** `GET /api/health` now reports real ingestion
counters (last poll duration, symbols processed, provider failures,
fallback-provider usage, LLM vs. template split) — in-process counters,
not a metrics platform, but enough to answer "is ingestion actually
working" from outside the process.

### Key Design Decisions

| Decision | Rationale |
|---|---|
| **Eager scoring + explanation, during ingestion** | Score was always computed at ingestion time; explanation generation used to be lazy (first read) and keyed per-user — both a latency risk and a source of redundant LLM calls (see Latency section). Moved both to ingestion: `GET /changes` is now a pure DB read for every user, always |
| **Real per-user auth (JWT)** | "What changed since you checked" needs a real per-user baseline, not a shared demo fiction |
| **Changes vs. Quotes are separate endpoints** | "What changed" (scored, filtered) and "what's the current price" (every tracked stock, always) are different questions — the brief asks for both |
| **Dynamic ticker resolution** | Adding a company validates and resolves it live against the provider instead of only matching a pre-seeded catalog |
| **Poll gated on either market being open** | NSE hours barely overlap US hours — gating on US-only silently starves Indian symbols |
| **Template fallback for LLM** | Works without a Gemini key, and survives the LLM being rate-limited or briefly unavailable |
| **Hallucination guard** | Rejects LLM responses with invented percentages before showing them to a user |
| **Commit-after-render** | Baseline only advances after the user has actually seen the change; a crashed tab sees it again |
| **Polling vs WebSockets** | Product is "return and see what changed," not a live trading ticker — polling matches that; tuned for a livelier feel without adding infrastructure |
| **Batched attention queries** | A 50-symbol watchlist used to mean ~7N queries in `get_changes`; now a fixed handful regardless of N (grouped observation/event/snapshot/news lookups) |
| **Timezone-aware DB timestamps everywhere** | A naive `datetime.utcnow()` default written to a `TIMESTAMPTZ` column gets silently reinterpreted as local time by this stack — confirmed by direct round-trip test, off by the local UTC offset. Every model default uses an aware `datetime.now(timezone.utc)` helper instead |

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

## Demo Mode

Live 5-minute demos shouldn't have to hope the market does something
interesting at the right moment. **Settings → Demo Mode → "Run demo
scenario"** (or `POST /api/admin/demo-scenario?watchlist_id=...`) seeds a
deterministic "you were away for 4h12m" scenario — NVDA +7.8% on 3.2x
volume with a news spike, TSLA -3.1% on 1.8x volume, MSFT +2.4%, plus two
quiet stocks (AAPL, AMZN) for contrast — through the **real** ingestion →
change-detection → scoring → explanation pipeline. Nothing is pre-baked:
`run_change_detection` runs for real, Gemini generates real explanations
for the seeded numbers. No external API calls are made, so it works fully
offline and produces the identical result every time.

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
├── app/
│   ├── config.py                    # Pydantic Settings (env vars)
│   ├── database.py                  # SQLAlchemy async engine
│   ├── models.py                    # ORM models (timezone-aware defaults)
│   ├── schemas.py                   # Pydantic request/response schemas
│   ├── main.py                      # FastAPI app + lifespan (starts scheduler)
│   │
│   ├── auth/
│   │   ├── security.py              # bcrypt hashing, JWT issue/verify
│   │   └── dependencies.py          # get_current_user FastAPI dependency
│   │
│   ├── engine/
│   │   ├── signals.py               # 5 pure signal functions
│   │   ├── scoring.py               # Weighted score + attention levels + event lifecycle
│   │   └── market_calendar.py       # US (ET) + Indian (IST) market hours
│   │
│   ├── providers/
│   │   ├── base.py                  # Abstract provider interface
│   │   ├── finnhub_provider.py      # US/global — quotes, candles, news, profile
│   │   └── yfinance_provider.py     # NSE/BSE — same interface, no API key needed
│   │
│   ├── services/
│   │   ├── ingestion_service.py     # Poll + change detection + provider fallback +
│   │   │                            # eager scoring/explanation (see Latency)
│   │   ├── attention_service.py     # Core "what changed?" pipeline — pure DB read
│   │   ├── explanation_service.py   # LLM + fallback + hallucination guard (called
│   │   │                            # from ingestion, never from a user request)
│   │   ├── observation_service.py   # Per-user baseline management
│   │   ├── watchlist_service.py     # CRUD + live ticker resolution + conflict check
│   │   └── demo_service.py          # Deterministic "you were away" scenario
│   │
│   ├── routers/
│   │   └── auth.py, health.py, watchlists.py, dashboard.py
│   │
│   ├── llm/
│   │   └── client.py, prompts.py, fallback.py
│   │
│   └── scheduler/
│       └── jobs.py                  # APScheduler — polls whenever either market is open
│
├── scripts/
│   ├── schema.sql, seed.py, pull_live_data.py   # one-shot manual data pull
│   └── benchmark_changes.py         # real latency measurement (see Latency)
│
└── tests/
    └── test_signals.py, test_scoring.py, test_fallback.py, test_ingestion.py, conftest.py

frontend/
└── src/
    ├── app/
    │   ├── page.tsx                       # Dashboard (Overview)
    │   ├── login/, signup/                # Auth pages
    │   ├── watchlists/, settings/         # Watchlist management, profile, demo mode
    │   └── stocks/[symbol]/page.tsx       # Stock detail + real price chart
    │
    ├── components/                        # AttentionCard, MarketOverview, Sidebar, etc.
    ├── context/
    │   └── AuthContext.tsx                # Token + user state
    ├── hooks/                             # React Query hooks (useChanges, useQuotes, useCandles, ...)
    └── lib/                               # api.ts, types.ts, countries.ts, auth-storage.ts
```

---

## Running Tests
```bash
cd backend
pytest -v
```

To reproduce the latency numbers in the [Latency](#latency-no-external-calls-in-the-user-request-path)
section against your own machine/DB (requires the containers from Quick
Start step 1 running):
```bash
python scripts/benchmark_changes.py
```

---

## API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/signup` | — | Create account (+ default watchlist) |
| POST | `/api/auth/login` | — | Returns a JWT |
| GET | `/api/auth/me` | ✓ | Current user |
| PATCH | `/api/auth/me` | ✓ | Update display name / country / timezone |
| GET | `/api/health` | — | Health check (DB connectivity) + real ingestion counters (last poll duration, symbols processed, provider failures, LLM/template split) |
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
| POST | `/api/admin/trigger-poll` | ✓ (+cooldown) | Manually trigger a market data poll — also the frontend's Refresh button |
| POST | `/api/admin/demo-scenario` | ✓ | Seed the deterministic demo scenario (see Demo Mode) |

---

## Scaling reasoning

The dimension that matters is **unique symbols tracked across all users**,
not users × symbols: `poll_market_data` fetches each distinct symbol from
the provider once per cycle regardless of how many users' watchlists
contain it (10,000 users all tracking NVDA still means one Finnhub call for
NVDA per poll). Per-user work — `attention_service.get_changes` — reads
already-stored state and is now batched to a fixed handful of queries per
request regardless of watchlist size (see Key Design Decisions). The actual
scaling constraint is the market-data provider's own rate limit, not the
database or the app tier; that's also why the poll interval and fallback
strategy are the parts this app treats seriously rather than a caching layer
that would just be hiding the real bottleneck.

---

## Known Limitations

Deliberate scope cuts, not oversights:

- **Single watchlist per user in the UI** — the schema supports multiple watchlists per user; only the first is surfaced.
- **No WebSocket push** — polling was the chosen tradeoff for this product shape (see Key Design Decisions).
- **No password reset / email verification** — auth is real (bcrypt + JWT) but minimal.
- **US-market candle backfill can be capped by Finnhub's free tier** — `/stock/candle` sometimes 403s on the free plan; live quotes are unaffected, and yfinance-backed Indian symbols aren't subject to this.
- **Conflict detection runs at ticker-resolution time, not on every poll** — a deliberate cost/benefit call, not an oversight (see Provider resilience above); it's a real, exercised code path, just not continuous.
- **No DB-fixture test infrastructure** — the existing suite is pure-function unit tests (signals, scoring, event lifecycle, hallucination guard, volume-baseline selection); N+1 batching, provider fallback, and the demo scenario are verified via live API calls rather than automated DB-backed tests.
- **`CONFLICTING`/`INVALID` quality statuses exist in the schema but aren't wired into every ingestion path** — `INVALID` in particular (rejecting malformed provider data outright) isn't implemented; providers currently already reject on missing/non-positive price before ever constructing a `QuoteData`, which covers the common case but isn't the same as a first-class rejection path.
- **`user_attention` is a vestigial table** — moving score/explanation onto `MarketEvent.signals` (see Latency) made it obsolete, but `schema.sql` still creates it. Left in place deliberately rather than risk a destructive migration for a hackathon-scope database; no application code reads or writes it anymore.
- **No ESLint config for the frontend** — `next lint` has never been run through its initial setup in this project; a pre-existing gap, not introduced by this pass.
