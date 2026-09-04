// TypeScript interfaces matching the backend Pydantic schemas.

export type AttentionLevel = "CRITICAL" | "HIGH" | "WATCH" | "NO_CHANGE";
export type DataFreshness = "FRESH" | "STALE";
export type ExplanationSource = "llm" | "template";

export interface NewsEventOut {
  id: string;
  headline: string;
  summary: string | null;
  source: string | null;
  url: string | null;
  published_at: string;
}

export interface SignalBreakdown {
  price_move: number;
  volume_spike: number;
  relative_move: number;
  breakout: number;
  news_surge: number;
  corroboration_boost: number;
}

export interface AttentionItem {
  symbol: string;
  company_name: string;
  sector: string | null;
  attention_level: AttentionLevel;
  score: number;
  confidence: number;
  explanation: string;
  explanation_source: ExplanationSource;
  event_type: string;
  magnitude: number | null;
  current_price: string | null;
  price_change_pct: number | null;
  volume: number | null;
  avg_volume_30d: number | null;
  benchmark_change_pct: number | null;
  latest_news: NewsEventOut[];
  signals: SignalBreakdown;
  detected_at: string;
  data_freshness: DataFreshness;
}

export interface ChangesResponse {
  watchlist_id: string;
  user_id: string;
  items: AttentionItem[];
  all_caught_up: boolean;
  generated_at: string;
}

export interface SymbolSearchResult {
  symbol: string;
  company_name: string;
  sector: string | null;
  exchange: string | null;
}

export interface WatchlistItemOut {
  id: string;
  symbol: {
    id: string;
    symbol: string;
    company_name: string;
    sector: string | null;
    exchange: string | null;
  };
  added_at: string;
}

export interface WatchlistOut {
  id: string;
  name: string;
  created_at: string;
  items: WatchlistItemOut[];
}

// ── Quotes (live market info, independent of attention scoring) ───────────────

export interface QuoteOut {
  symbol: string;
  company_name: string;
  sector: string | null;
  exchange: string | null;
  current_price: string | null;
  price_change_pct: number | null;
  volume: number | null;
  data_freshness: "FRESH" | "STALE" | "NO_DATA";
}

export interface DashboardSummary {
  total_symbols_tracked: number;
  symbols_with_events: number;
  critical_count: number;
  high_count: number;
  watch_count: number;
  last_poll_at: string | null;
  last_checked_at: string | null;
  market_open: boolean;
  us_market_open: boolean;
  indian_market_open: boolean;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  display_name: string;
  country: string | null;
  timezone: string;
  created_at: string;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export interface UpdateProfileRequest {
  display_name?: string;
  country?: string;
  timezone?: string;
}

// ── Candles ───────────────────────────────────────────────────────────────────

export interface CandlePoint {
  timestamp: string;
  price: string;
  volume: number | null;
}

export type CandleRange = "1D" | "1W" | "1M";

export interface CandlesResponse {
  symbol: string;
  range: CandleRange;
  points: CandlePoint[];
}
