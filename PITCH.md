# Product Pitch

Most watchlists show you a price. This one tells you whether that price
actually matters. Every tracked stock (US via Finnhub, Indian NSE/BSE via
yfinance) is scored against five weighted signals — price move, volume,
relative-to-market move, breakout, news surge. Below-threshold noise is
filtered out; what's left gets a plain-English explanation (Gemini,
hallucination-guarded, template fallback) and a live sparkline. It's fast
because a stock app has to be: the read path never waits on Finnhub,
yfinance, or Gemini — explanations are generated once during background
ingestion, not per user per view — measured at 30-70ms for 5-100 stocks,
benchmarked, not claimed. Real per-user accounts make "since you checked"
a genuine baseline, not a demo fiction. The bet: a watchlist's job is
triage, not decoration.
