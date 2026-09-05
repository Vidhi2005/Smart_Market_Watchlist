"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AnimatePresence } from "framer-motion";
import { AlertTriangle, RefreshCw, CheckCheck } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { GreetingHero } from "@/components/GreetingHero";
import { AttentionCard } from "@/components/AttentionCard";
import { AttentionSummary } from "@/components/AttentionSummary";
import { AllCaughtUp } from "@/components/AllCaughtUp";
import { MarketOverview } from "@/components/MarketOverview";
import { MarketPulse } from "@/components/MarketPulse";
import { CardSkeleton } from "@/components/Skeleton";
import { StockSearch } from "@/components/StockSearch";
import { useChanges, useCommitObservations } from "@/hooks/useChanges";
import { useDashboard, useWatchlists } from "@/hooks/useDashboard";
import { useQuotes } from "@/hooks/useQuotes";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";

function DashboardContent() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const { data: watchlists } = useWatchlists();
  const watchlistId = watchlists?.[0]?.id ?? null;

  const { data: dashboard } = useDashboard();
  // Default true (normal cadence) until we actually know a market's
  // closed — never silently under-poll before the first dashboard load.
  const marketOpen = dashboard ? dashboard.us_market_open || dashboard.indian_market_open : true;

  const { data: changes, isLoading, error } = useChanges(watchlistId, marketOpen);
  const { data: quotes, isLoading: quotesLoading } = useQuotes(watchlistId, marketOpen);
  const commitMutation = useCommitObservations(watchlistId ?? "");

  const [polling, setPolling] = useState(false);
  const [reviewedCount, setReviewedCount] = useState<number | null>(null);

  const items = changes?.items ?? [];

  // Observations are only ever committed on an explicit user action —
  // "Mark reviewed" (one symbol) or "Mark all as reviewed" (the whole
  // watchlist) below. Nothing here auto-commits based on rendering,
  // polling, or time elapsed: a market event stays visible until the
  // user says they've reviewed it.
  const handleMarkAllReviewed = async () => {
    const count = items.length;
    await commitMutation.mutateAsync(undefined);
    setReviewedCount(count);
    setTimeout(() => setReviewedCount(null), 3000);
  };

  const handleMarkReviewed = (symbolId: string) => {
    commitMutation.mutate([symbolId]);
  };

  const handleTriggerPoll = async () => {
    setPolling(true);
    try {
      await api.triggerPoll();
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ["changes"] });
        qc.invalidateQueries({ queryKey: ["dashboard"] });
        qc.invalidateQueries({ queryKey: ["quotes"] });
        setPolling(false);
      }, 3000);
    } catch {
      setPolling(false);
    }
  };

  const criticalCount = items.filter((i) => i.attention_level === "CRITICAL").length;
  const highCount    = items.filter((i) => i.attention_level === "HIGH").length;
  const watchCount   = items.filter((i) => i.attention_level === "WATCH").length;
  const hasStale     = items.some((i) => i.data_freshness === "STALE");

  const watchlistItems = watchlists?.[0]?.items ?? [];
  const flaggedSymbols = new Set(items.map((i) => i.symbol));

  return (
    <>
      <GreetingHero
        displayName={user?.display_name ?? ""}
        timezone={user?.timezone ?? "UTC"}
        items={items}
        lastCheckedAt={dashboard?.last_checked_at ?? null}
      />

      {hasStale && (
        <div
          className="card"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            marginBottom: 20,
            background: "var(--clr-high-bg)",
            borderColor: "var(--clr-high-border)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13 }}>
            <AlertTriangle size={16} color="var(--clr-high)" />
            Some market data is stale. Showing the last validated snapshot where fresh data is unavailable.
          </div>
          <button
            className="btn btn-ghost"
            style={{ fontSize: 12, flexShrink: 0 }}
            onClick={() => qc.invalidateQueries({ queryKey: ["changes"] })}
            id="retry-stale-btn"
          >
            <RefreshCw size={12} /> Retry
          </button>
        </div>
      )}

      {/* Summary stats */}
      <AttentionSummary
        total={dashboard?.total_symbols_tracked ?? 0}
        critical={criticalCount}
        high={highCount}
        watch={watchCount}
      />

      <MarketPulse items={items} quotes={quotes ?? []} />

      {/* Two-column layout: sidebar + cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "280px 1fr",
          gap: 24,
          alignItems: "start",
        }}
      >
        {/* ── Watchlist panel ── */}
        <aside>
          <div className="card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>My Watchlist</h2>
              <p style={{ fontSize: 12, color: "var(--clr-text-muted)" }}>
                {watchlistItems.length} symbol{watchlistItems.length === 1 ? "" : "s"} tracked
              </p>
            </div>

            {watchlistId && (
              <StockSearch
                watchlistId={watchlistId}
                onAdded={() => {
                  qc.invalidateQueries({ queryKey: ["watchlists"] });
                  qc.invalidateQueries({ queryKey: ["quotes"] });
                }}
              />
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {watchlistItems.map((item) => (
                <div
                  key={item.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "6px 8px",
                    borderRadius: "var(--radius-sm)",
                    background: "var(--clr-surface-2)",
                    fontSize: 13,
                  }}
                >
                  <span style={{ fontWeight: 600 }}>{item.symbol.symbol}</span>
                  <span style={{ color: "var(--clr-text-muted)", fontSize: 11 }}>
                    {item.symbol.exchange}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {dashboard?.last_poll_at && (
            <div style={{ marginTop: 12, fontSize: 11, color: "var(--clr-text-faint)", textAlign: "center" }}>
              Last data poll: {new Date(dashboard.last_poll_at).toLocaleTimeString()}
            </div>
          )}
        </aside>

        {/* ── Main content ── */}
        <section id="attention-list" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {items.length > 0 && (
            <>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 12,
                }}
              >
                <div
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    color: "var(--clr-text-muted)",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                  }}
                >
                  Attention required · {items.length} item{items.length > 1 ? "s" : ""}
                </div>

                {reviewedCount !== null ? (
                  <div style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12, color: "var(--clr-text-muted)" }}>
                    <CheckCheck size={13} /> {reviewedCount} item{reviewedCount === 1 ? "" : "s"} reviewed
                  </div>
                ) : (
                  <button
                    className="btn btn-ghost"
                    style={{ fontSize: 12 }}
                    onClick={handleMarkAllReviewed}
                    disabled={commitMutation.isPending}
                    id="mark-all-reviewed-btn"
                  >
                    <CheckCheck size={13} /> Mark all as reviewed
                  </button>
                )}
              </div>

              <AnimatePresence initial={false}>
                {items.map((item, i) => (
                  <AttentionCard
                    key={`${item.symbol}-${item.detected_at}`}
                    item={item}
                    index={i}
                    onMarkReviewed={handleMarkReviewed}
                    isMarking={commitMutation.isPending}
                  />
                ))}
              </AnimatePresence>
            </>
          )}

          {isLoading && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {[...Array(3)].map((_, i) => <CardSkeleton key={i} />)}
            </div>
          )}

          {error && (
            <div
              className="card"
              style={{
                borderColor: "var(--clr-critical-border)",
                color: "var(--clr-critical)",
                textAlign: "center",
              }}
            >
              Failed to load changes. Is the backend running?
            </div>
          )}

          {!isLoading && !error && changes?.all_caught_up && <AllCaughtUp />}

          {/* Live price for every tracked stock — not just flagged ones */}
          <MarketOverview quotes={quotes ?? []} flaggedSymbols={flaggedSymbols} isLoading={quotesLoading} />
        </section>
      </div>
    </>
  );
}

export default function DashboardPage() {
  return (
    <AppShell>
      <DashboardContent />
    </AppShell>
  );
}
