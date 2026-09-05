"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Trash2, Loader2 } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { StockSearch } from "@/components/StockSearch";
import { Sparkline } from "@/components/Sparkline";
import { useWatchlists } from "@/hooks/useDashboard";
import { useQuotes } from "@/hooks/useQuotes";
import { api } from "@/lib/api";

function WatchlistsContent() {
  const qc = useQueryClient();
  const { data: watchlists, isLoading } = useWatchlists();
  const watchlist = watchlists?.[0];
  const { data: quotes } = useQuotes(watchlist?.id ?? null);
  const [removing, setRemoving] = useState<string | null>(null);

  const priceBySymbol = new Map((quotes ?? []).map((q) => [q.symbol, q]));

  const handleRemove = async (symbolId: string) => {
    if (!watchlist) return;
    setRemoving(symbolId);
    try {
      await api.removeSymbol(watchlist.id, symbolId);
      qc.invalidateQueries({ queryKey: ["watchlists"] });
      qc.invalidateQueries({ queryKey: ["quotes"] });
      qc.invalidateQueries({ queryKey: ["changes"] });
    } finally {
      setRemoving(null);
    }
  };

  return (
    <>
      <h1 style={{ fontSize: 22, fontWeight: 800, marginBottom: 4 }}>Watchlists</h1>
      <p style={{ fontSize: 13, color: "var(--clr-text-muted)", marginBottom: 24 }}>
        Manage the companies you track.
      </p>

      {isLoading && <div className="skeleton" style={{ height: 200, width: "100%" }} />}

      {!isLoading && watchlist && (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ padding: 20, borderBottom: "1px solid var(--clr-border)" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
              <div>
                <h2 style={{ fontSize: 15, fontWeight: 700 }}>{watchlist.name}</h2>
                <p style={{ fontSize: 12, color: "var(--clr-text-muted)", marginTop: 2 }}>
                  {watchlist.items.length} compan{watchlist.items.length === 1 ? "y" : "ies"} tracked
                </p>
              </div>
            </div>
            <StockSearch
              watchlistId={watchlist.id}
              onAdded={() => {
                qc.invalidateQueries({ queryKey: ["watchlists"] });
                qc.invalidateQueries({ queryKey: ["quotes"] });
              }}
            />
          </div>

          {watchlist.items.length === 0 ? (
            <div style={{ padding: 32, textAlign: "center", color: "var(--clr-text-faint)", fontSize: 13 }}>
              Nothing tracked yet — search above to add your first company.
            </div>
          ) : (
            <div>
              {watchlist.items.map((item) => {
                const q = priceBySymbol.get(item.symbol.symbol);
                const pct = q?.price_change_pct ?? null;
                const isUp = pct !== null ? pct >= 0 : true;
                return (
                  <div
                    key={item.id}
                    className="watchlist-row"
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: 16,
                      padding: "14px 20px",
                      borderBottom: "1px solid var(--clr-border)",
                    }}
                  >
                    <div style={{ minWidth: 0, flexShrink: 0 }}>
                      <div style={{ fontWeight: 700, fontSize: 14 }}>
                        {item.symbol.symbol}
                        {item.symbol.exchange && (
                          <span className="chip" style={{ marginLeft: 8, fontSize: 10, padding: "2px 8px" }}>
                            {item.symbol.exchange}
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--clr-text-muted)", marginTop: 2 }}>
                        {item.symbol.company_name}
                        {item.symbol.sector ? ` · ${item.symbol.sector}` : ""}
                      </div>
                    </div>

                    <div style={{ flex: 1, minWidth: 90, maxWidth: 130 }}>
                      <Sparkline symbol={item.symbol.symbol} isUp={isUp} />
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: 20, flexShrink: 0 }}>
                      <div className="tabular-nums" style={{ textAlign: "right" }}>
                        <div style={{ fontWeight: 700, fontSize: 14 }}>
                          {q?.current_price ? `$${Number(q.current_price).toFixed(2)}` : "—"}
                        </div>
                        {pct !== null && (
                          <div className={pct >= 0 ? "positive" : "negative"} style={{ fontSize: 12, fontWeight: 600 }}>
                            {pct >= 0 ? "+" : ""}{pct.toFixed(2)}%
                          </div>
                        )}
                      </div>

                      <button
                        onClick={() => handleRemove(item.symbol.id)}
                        disabled={removing === item.symbol.id}
                        id={`remove-${item.symbol.symbol}-btn`}
                        title="Remove from watchlist"
                        style={{
                          background: "none",
                          border: "1px solid var(--clr-border)",
                          borderRadius: "var(--radius-sm)",
                          width: 32,
                          height: 32,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          cursor: "pointer",
                          color: "var(--clr-text-muted)",
                        }}
                      >
                        {removing === item.symbol.id ? <Loader2 size={14} className="spin" /> : <Trash2 size={14} />}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </>
  );
}

export default function WatchlistsPage() {
  return (
    <AppShell>
      <WatchlistsContent />
    </AppShell>
  );
}
