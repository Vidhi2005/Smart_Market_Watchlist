# Product Pitch

Most watchlists show you a price. This one tells you whether that price
actually matters. Every tracked stock is scored against five weighted
signals — price move, volume, relative-to-market move, breakout, news
surge — fed by a provider chain that genuinely fails over (Finnhub →
Twelve Data → yfinance for US, live-verified against real quotes, not
assumed) and flags cross-provider disagreement instead of averaging it
away. Below-threshold noise is filtered out; what's left gets a
plain-English explanation (Gemini, hallucination-guarded, template
fallback) and a live sparkline. It's fast because a stock app has to be:
the read path never waits on a provider or an LLM — explanations are
generated once during background ingestion — measured at 30-70ms for
5-100 stocks, benchmarked, not claimed. Real per-user accounts make
"since you checked" a genuine baseline, not a demo fiction. The bet: a
watchlist's job is triage, not decoration.
