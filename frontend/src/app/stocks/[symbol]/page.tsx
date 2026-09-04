"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { WatchlistOut } from "@/lib/types";
import { SignalBreakdownBars } from "@/components/SignalBreakdown";
import { FreshnessIndicator } from "@/components/FreshnessIndicator";
import { CardSkeleton } from "@/components/Skeleton";
import { PriceChart } from "@/components/PriceChart";
import { RequireAuth } from "@/components/RequireAuth";

// We derive stock detail from the changes response to avoid a new endpoint
function useStockDetail(symbol: string) {
  const { data: watchlists } = useQuery<WatchlistOut[]>({
    queryKey: ["watchlists"],
    queryFn: api.getWatchlists,
  });
  const watchlistId = watchlists?.[0]?.id ?? null;

  return useQuery({
    queryKey: ["changes", watchlistId, "detail", symbol],
    queryFn: async () => {
      if (!watchlistId) return null;
      const changes = await api.getChanges(watchlistId);
      return changes.items.find((i) => i.symbol === symbol.toUpperCase()) ?? null;
    },
    enabled: !!watchlistId,
    refetchInterval: 30_000,
  });
}

function StockDetailInner() {
  const { symbol } = useParams() as { symbol: string };
  const { data: item, isLoading } = useStockDetail(symbol);
  const upperSymbol = symbol.toUpperCase();

  return (
    <div style={{ minHeight: "100vh", background: "var(--clr-bg)" }}>
      {/* Simple header */}
      <header
        style={{
          padding: "20px 24px",
          borderBottom: "1px solid var(--clr-border)",
          display: "flex",
          alignItems: "center",
          gap: 16,
        }}
      >
        <Link
          href="/"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            color: "var(--clr-text-muted)",
            textDecoration: "none",
            fontSize: 14,
          }}
        >
          <ArrowLeft size={16} /> Dashboard
        </Link>
        <h1 style={{ fontSize: 20, fontWeight: 800 }}>{upperSymbol}</h1>
      </header>

      <main className="container" style={{ paddingBlock: 32 }}>
        {isLoading && <CardSkeleton />}

        {!isLoading && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {item ? (
              <>
                {/* Header card */}
                <div className="card">
                  <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
                    <div>
                      <div style={{ fontSize: 13, color: "var(--clr-text-muted)", marginBottom: 4 }}>
                        {item.company_name} · {item.sector}
                      </div>
                      <div style={{ fontSize: 40, fontWeight: 900, letterSpacing: "-0.04em" }} className="tabular-nums">
                        ${Number(item.current_price).toFixed(2)}
                      </div>
                      <div
                        className={(item.price_change_pct ?? 0) >= 0 ? "positive" : "negative"}
                        style={{ fontSize: 18, fontWeight: 700, marginTop: 4 }}
                      >
                        {(item.price_change_pct ?? 0) >= 0 ? "+" : ""}{(item.price_change_pct ?? 0).toFixed(2)}% today
                      </div>
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8 }}>
                      <FreshnessIndicator freshness={item.data_freshness} detectedAt={item.detected_at} />
                      {item.volume && (
                        <div style={{ fontSize: 12, color: "var(--clr-text-muted)" }}>
                          Volume: {item.volume.toLocaleString()}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <PriceChart symbol={upperSymbol} />

                {/* Explanation */}
                <div className="card">
                  <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Why it&apos;s flagged</h2>
                  <p style={{ fontSize: 15, lineHeight: 1.7 }}>
                    {item.explanation}
                    {item.explanation_source === "llm" && (
                      <span style={{ marginLeft: 8, fontSize: 11, color: "var(--clr-accent)", fontWeight: 600 }}>
                        AI
                      </span>
                    )}
                  </p>
                </div>

                {/* Signal breakdown */}
                <div className="card">
                  <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>Signal Breakdown</h2>
                  <SignalBreakdownBars signals={item.signals} />
                </div>

                {/* News */}
                {item.latest_news.length > 0 && (
                  <div className="card">
                    <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Recent News</h2>
                    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                      {item.latest_news.map((n) => (
                        <div key={n.id} style={{ borderBottom: "1px solid var(--clr-border)", paddingBottom: 12 }}>
                          <a
                            href={n.url ?? "#"}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              fontSize: 14,
                              fontWeight: 500,
                              color: "var(--clr-text)",
                              textDecoration: "none",
                              lineHeight: 1.5,
                            }}
                          >
                            {n.headline}
                          </a>
                          <div style={{ marginTop: 4, fontSize: 11, color: "var(--clr-text-muted)" }}>
                            {n.source} · {new Date(n.published_at).toLocaleDateString()}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="card" style={{ textAlign: "center", color: "var(--clr-text-muted)" }}>
                No active alert for {upperSymbol} since your last visit — showing real price history below.
              </div>
            )}

            {!item && <PriceChart symbol={upperSymbol} />}
          </div>
        )}
      </main>
    </div>
  );
}

export default function StockDetailPage() {
  return (
    <RequireAuth>
      <StockDetailInner />
    </RequireAuth>
  );
}
