# Smart Market Watchlist

**An attention engine for your stock watchlist.**

## The Pitch

Most watchlists show you a price. This one tells you whether that price
actually matters. A watchlist's real job is triage, not decoration — so
every tracked stock (US and Indian equities, each on its own market
calendar) is scored against five weighted signals — price move, volume,
relative-to-market move, breakout, news surge — and below-threshold noise
is filtered out entirely. What's left gets a plain-English explanation
and a live sparkline, and "since you checked" is a genuine per-user
baseline (real accounts, not a shared demo fiction), kept distinct from
"today's move" because they honestly answer different questions.

**How it's designed.** The core bet is a strict split between *global
market state* (symbols, prices, events — computed once, shared by every
user tracking that symbol) and *per-user observation state* (your own
"last checked" baseline). That split is what makes "since you checked"
possible without duplicating work per user. Market data comes through a
provider chain that genuinely fails over — live-tested against real
endpoints, not assumed from documentation — and flags cross-provider
disagreement instead of silently averaging it away. Explanations (Gemini,
hallucination-guarded, with a template fallback) are generated once per
event during background ingestion, never in a user's request — so the
read path never waits on a provider or an LLM, measured at 30-70ms for
5-100 stocks, benchmarked rather than claimed.

**The thinking behind the key choices**, in short: real auth because a
fake per-user baseline would make the whole premise a demo trick; polling
over WebSockets because the product is "see what changed," not a live
trading ticker, so the added infrastructure wouldn't buy anything real;
an event only fires on an actual state transition, not every poll a stock
stays elevated, because that's the difference between an alert and noise;
and every resilience claim below is something that was actually tested
against a live endpoint, not inferred from a pricing page — including the
provider that got built, verified, and deliberately left switched off
because its real limits didn't fit the job. The full reasoning for each
is in [Key Design Decisions](#key-design-decisions) and
[Provider resilience](#provider-resilience) below.

---

**Contents:** [Architecture](#architecture) ·
[Core idea: global market state vs. per-user observation](#global-market-state-vs-per-user-observation) ·
[Provider resilience](#provider-resilience) ·
[Latency](#latency) ·
[Design decisions](#key-design-decisions) ·
[Scoring](#scoring) ·
[Demo Mode](#demo-mode) ·
[Quick Start](#quick-start) ·
[Project Structure](#project-structure) ·
[API Reference](#api-reference) ·
[Known Limitations](#known-limitations)

---

## Architecture

```
┌─────────────────────────────────────┐
│       Next.js Frontend (:3000)       │
│     React Query · adaptive polling   │
└──────────────────┬────────────────────┘
                    │ HTTP/REST + JWT bearer
┌───────────────────▼────────────────────┐
│        FastAPI Backend (:8000)          │
│        APScheduler · JWT auth           │
└────┬─────────┬─────────┬─────────┬──────┘
     │         │         │         │
     ▼         ▼         ▼         ▼
 Finnhub +  yfinance  PostgreSQL  Gemini
 Twelve Data (NSE/BSE)    DB     LLM API
  (US/global)
```

Symbols are routed to a per-market provider chain by ticker suffix
(`.NS`/`.BO` → yfinance, everything else → Finnhub → Twelve Data as
fallback) — a genuine US + Indian equities tracker, each on its own
market calendar, not a single US-only clock with an Indian ticker
bolted on.

## Global market state vs. per-user observation

The idea the whole product rests on:

```
MARKET STATE IS GLOBAL.        (symbols, snapshots, events, news)
OBSERVATION STATE IS PER-USER.  (last_observed_at, last_observed_snapshot_id)
```

Ingestion and change detection never know or care which user is looking —
one poll of NVDA serves everyone tracking it. `attention_service` is
where the two meet: it reads a user's own baseline to compute **"since
you checked"** (distinct from "today's move," which is real context but
answers a different question — two users who added NVDA at different
times see different "since checked" numbers from the same underlying
event). A symbol also doesn't re-alert on every poll just for staying
elevated — an event is only created on a real transition (new, escalated,
de-escalated), not once per poll cycle.

## Provider resilience

Three market-data providers, wired into per-market fallback chains
(`us_provider_chain` / `india_provider_chain` — comma-separated, config
not code) that walk in order and stop at the first success. Every claim
below came from live-testing the actual endpoints, not the docs:

- **Twelve Data** is a real, active US fallback — verified against real
  quotes that independently matched a second provider's numbers for the
  same symbol.
- **Alpha Vantage** is built and tested, but deliberately *not* active —
  its free tier is 25 requests/day total, confirmed live, nowhere near
  enough for a polling loop. Kept available rather than forced in because
  a key exists.
- **Twelve Data is not in India's chain** — live-tested against
  `RELIANCE.NS` and its own documented `RELIANCE:NSE`/`exchange=NSE`
  formats; all three came back with *"available starting with the Grow or
  Venture plan."* A real capability limit, confirmed rather than assumed,
  so yfinance stays India's only provider.
- **Exception-safe fallback**: a provider adapter catches its own known
  failure modes (timeout, HTTP error, rate limit, bad JSON) and moves to
  the next provider — but an unexpected exception is never silently
  treated as "provider unavailable."
- **Conflict detection, not silent averaging**: adding a new ticker
  cross-checks it against every other configured provider once; a >2%
  disagreement is returned on the API response and shown as *"Finnhub and
  Twelve Data differ by 2.8% — using Finnhub's value"* — never "incorrect
  data," since a difference can be feed timing, not necessarily either
  source being wrong.
- **Per-provider health** in `GET /api/health` (`provider_failures` keyed
  by name), not just one aggregate counter.

Volume baselines follow the same honesty principle: `is_daily_bar`
distinguishes real daily OHLCV rows from live-poll rows, since live polls
can carry intraday-cumulative or absent volume that isn't comparable to a
single day's figure.

## Latency

`GET /changes` used to be able to call Gemini synchronously — the actual
bug was explanations cached per `(user_id, event_id)` even though an
explanation doesn't depend on who's asking. Moved generation into
background ingestion, stored once per event; the read path is now a pure
DB query with no LLM or provider call possible in it, structurally.

Measured with `scripts/benchmark_changes.py` (real DB rows, no
network/LLM):

| Symbols | min (ms) | avg (ms) | max (ms) |
|---|---|---|---|
| 5   | 28.5 | 31.6 | 35.5 |
| 20  | 36.2 | 36.9 | 38.4 |
| 50  | 42.6 | 45.2 | 47.7 |
| 100 | 56.8 | 67.2 | 72.8 |

20x more symbols costs roughly 2x latency, not 20x. `useChanges`/`useQuotes`
poll every 15s while a relevant market is open, backing off to 2 minutes
when both are closed, and stop entirely on a backgrounded tab.

> Run the frontend with `npm run build && npm start` rather than `npm run
> dev` to see this for real — dev mode's per-route on-demand compilation
> adds multi-second first-visit delays a real deployment never has.
> Production: every route under 30ms, most single-digit.

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Eager scoring + explanation, during ingestion** | `GET /changes` is a pure DB read for every user, always — see Latency |
| **Real per-user auth (JWT)** | "Since you checked" needs a genuine per-user baseline, not a shared fiction |
| **Changes vs. Quotes are separate endpoints** | "What changed" (scored, filtered) and "current price" (every tracked stock, always) are different questions |
| **Dynamic ticker resolution** | Adding a company validates and resolves it live instead of matching a fixed catalog |
| **Poll gated on either market being open** | NSE and US hours barely overlap — gating on US-only would starve Indian symbols |
| **Template fallback for the LLM** | Works with no Gemini key, and survives it being rate-limited |
| **Hallucination guard** | Rejects LLM output with invented percentages before it reaches a user |
| **Commit-after-render** | Baseline only advances after the user explicitly reviews a change |
| **Polling, not WebSockets** | The product is "see what changed," not a live trading ticker — polling matches that without added infrastructure |
| **Batched attention queries** | A fixed handful of queries per request regardless of watchlist size |
| **Timezone-aware timestamps everywhere** | A naive UTC default silently gets reinterpreted as local time by this stack — fixed at the model layer |

## Scoring

| Signal | Weight |
|---|---|
| Price Move | 35% |
| Relative Move (vs. market) | 25% |
| Volume Spike | 20% |
| News Surge | 10% |
| Breakout | 10% |

Corroboration boost: 2 signals agreeing → +5%, 3 → +10%, 4+ → +15%.
Attention levels: CRITICAL (≥0.70) · HIGH (≥0.40) · WATCH (≥0.15).

## Demo Mode

**Settings → Demo Mode → "Run demo scenario"** seeds a deterministic "you
were away for 4h12m" scenario — NVDA +7.8% on 3.2x volume with a news
spike, TSLA -3.1%, MSFT +2.4%, plus two quiet stocks for contrast —
through the real ingestion → scoring → explanation pipeline. Nothing is
pre-baked and no external API calls are made, so it's fully offline and
identical every time.

---

## Quick Start

### Prerequisites
- Docker Desktop, Python 3.9+, Node.js 18+
- A [Finnhub](https://finnhub.io) API key (free tier)
- A Gemini API key (optional — template fallback works without it)

```bash
# 1. Database
docker compose up -d

# 2. Backend
cd backend
cp .env.example .env   # set FINNHUB_API_KEY, JWT_SECRET_KEY, optionally GEMINI_API_KEY
python -m venv .venv && .venv/Scripts/activate   # .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
python scripts/seed.py   # idempotent — seeds symbols + demo@smartwatchlist.dev / demo12345
uvicorn app.main:app --reload

# 3. Frontend
cd ../frontend
cp .env.local.example .env.local
npm install
npm run dev   # or: npm run build && npm start for production-accurate latency
```

Open `http://localhost:3000` — sign up, or log in with the demo account.

Run tests: `cd backend && pytest -v`. Reproduce the latency table:
`python scripts/benchmark_changes.py`.

---

## Project Structure

```
backend/app/
├── engine/          signals.py, scoring.py, market_calendar.py
├── providers/       base.py + finnhub, yfinance, twelve_data, alpha_vantage
├── services/        ingestion, attention, explanation, observation, watchlist, demo
├── routers/         auth, health, watchlists, dashboard
├── llm/             Gemini client + template fallback + hallucination guard
└── scheduler/       APScheduler jobs

frontend/src/
├── app/             page.tsx (dashboard), login/, signup/, watchlists/, settings/, stocks/[symbol]/
├── components/       AttentionCard, MarketPulse, MarketOverview, Sidebar, ...
├── hooks/           useChanges, useQuotes, useCandles, ...
└── lib/             api.ts, types.ts
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/signup` / `/login` | Account creation / JWT |
| GET | `/api/health` | DB status + real ingestion/provider counters |
| GET/POST | `/api/watchlists` | List / create watchlists |
| GET | `/api/watchlists/{id}/changes` | Ranked, scored attention items |
| GET | `/api/watchlists/{id}/quotes` | Live price for every tracked symbol |
| POST | `/api/watchlists/{id}/symbols` | Add a symbol — live-resolved, includes `provider_conflict` if providers disagreed |
| GET | `/api/stocks/{symbol}/candles` | Historical price points |
| POST | `/api/observations/commit` | Advance "last checked" baseline |
| GET | `/api/dashboard` | Per-user summary + market hours |
| POST | `/api/admin/demo-scenario` | Seed the demo scenario |

---

## Known Limitations

Deliberate scope cuts:

- Single watchlist surfaced in the UI (schema supports more).
- No WebSocket push — polling fits this product's actual shape.
- No password reset / email verification.
- Conflict detection runs at ticker-add time, not continuously (would
  double ongoing API calls against free-tier limits for marginal gain).
- No DB-fixture test infra — tests are pure-function and mocked-provider
  unit tests; N+1 batching and the demo scenario are verified via live
  API calls instead.
- `CONFLICTING`/`INVALID` quality statuses exist in the schema but aren't
  wired into every path yet.
- No ESLint config on the frontend.
