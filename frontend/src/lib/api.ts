// Typed fetch client for the backend API.

import { clearToken, getToken } from "./auth-storage";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("smw:unauthorized"));
    }
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      // body wasn't JSON — fall back to statusText
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Watchlists ────────────────────────────────────────────────────────────────

import type {
  AuthResponse,
  CandleRange,
  CandlesResponse,
  ChangesResponse,
  DashboardSummary,
  QuoteOut,
  SymbolSearchResult,
  User,
  WatchlistItemOut,
  WatchlistOut,
} from "./types";

export const api = {
  // Auth
  signup: (email: string, password: string, displayName: string, country: string, timezone: string) =>
    apiFetch<AuthResponse>("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password, display_name: displayName, country, timezone }),
    }),

  login: (email: string, password: string) =>
    apiFetch<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  getMe: () => apiFetch<User>("/api/auth/me"),

  updateProfile: (payload: { display_name?: string; country?: string; timezone?: string }) =>
    apiFetch<User>("/api/auth/me", {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  // Watchlists
  getWatchlists: () => apiFetch<WatchlistOut[]>("/api/watchlists"),

  getChanges: (watchlistId: string) =>
    apiFetch<ChangesResponse>(`/api/watchlists/${watchlistId}/changes`),

  getQuotes: (watchlistId: string) =>
    apiFetch<QuoteOut[]>(`/api/watchlists/${watchlistId}/quotes`),

  addSymbol: (watchlistId: string, symbol: string) =>
    apiFetch<WatchlistItemOut>(`/api/watchlists/${watchlistId}/symbols`, {
      method: "POST",
      body: JSON.stringify({ symbol }),
    }),

  removeSymbol: (watchlistId: string, symbolId: string) =>
    apiFetch(`/api/watchlists/${watchlistId}/symbols/${symbolId}`, {
      method: "DELETE",
    }),

  // Observations
  commitObservations: (watchlistId: string, symbolIds?: string[]) =>
    apiFetch("/api/observations/commit", {
      method: "POST",
      body: JSON.stringify({ watchlist_id: watchlistId, symbol_ids: symbolIds ?? null }),
    }),

  // Stocks
  searchStocks: (query: string) =>
    apiFetch<SymbolSearchResult[]>(`/api/stocks/search?q=${encodeURIComponent(query)}`),

  getCandles: (symbol: string, range: CandleRange) =>
    apiFetch<CandlesResponse>(
      `/api/stocks/${encodeURIComponent(symbol)}/candles?range=${range}`
    ),

  // Dashboard
  getDashboard: () => apiFetch<DashboardSummary>("/api/dashboard"),

  // Health
  getHealth: () => apiFetch<{ status: string; db: string; version: string }>("/api/health"),

  // Admin
  triggerPoll: () => apiFetch("/api/admin/trigger-poll", { method: "POST" }),

  runDemoScenario: (watchlistId: string) =>
    apiFetch<{ scenario: string; away_for_minutes: number; symbols: string[] }>(
      `/api/admin/demo-scenario?watchlist_id=${encodeURIComponent(watchlistId)}`,
      { method: "POST" }
    ),
};
