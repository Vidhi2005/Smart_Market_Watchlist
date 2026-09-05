"use client";

import Link from "next/link";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { QuoteOut } from "@/lib/types";
import { FreshnessIndicator } from "./FreshnessIndicator";
import { StockAvatar } from "./StockAvatar";

interface Props {
  quotes: QuoteOut[];
  flaggedSymbols: Set<string>;
  isLoading: boolean;
}

function formatVolume(v: number | null): string {
  if (!v) return "—";
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
  return String(v);
}

/**
 * Live price for every tracked symbol, regardless of whether it triggered an
 * attention event. "What changed" (AttentionCard) and "what's the current
 * price" (this table) are separate questions — a quiet stock still has a
 * real price a user should be able to see.
 */
export function MarketOverview({ quotes, flaggedSymbols, isLoading }: Props) {
  if (isLoading) {
    return <div className="skeleton" style={{ height: 220, width: "100%" }} />;
  }

  if (quotes.length === 0) {
    return (
      <div className="card" style={{ textAlign: "center", color: "var(--clr-text-faint)", fontSize: 13 }}>
        Add a company to your watchlist to see live market data here.
      </div>
    );
  }

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      <div style={{ padding: "16px 20px 0" }}>
        <h2 style={{ fontSize: 14, fontWeight: 700 }}>Market Overview</h2>
        <p style={{ fontSize: 12, color: "var(--clr-text-muted)", marginTop: 2 }}>
          Live price for every stock you track, updated as new data arrives.
        </p>
      </div>

      <div style={{ overflowX: "auto", marginTop: 12 }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ borderTop: "1px solid var(--clr-border)", borderBottom: "1px solid var(--clr-border)" }}>
              {["Symbol", "Price", "Change", "Volume", "Status", ""].map((h) => (
                <th
                  key={h}
                  style={{
                    textAlign: h === "Symbol" ? "left" : "right",
                    padding: "10px 20px",
                    fontSize: 11,
                    fontWeight: 700,
                    color: "var(--clr-text-muted)",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {quotes.map((q) => {
              const pct = q.price_change_pct;
              const isUp = (pct ?? 0) > 0;
              const isDown = (pct ?? 0) < 0;
              const flagged = flaggedSymbols.has(q.symbol);

              return (
                <tr
                  key={q.symbol}
                  className="hover-row"
                  style={{ borderBottom: "1px solid var(--clr-border)" }}
                >
                  <td style={{ padding: "12px 20px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <StockAvatar symbol={q.symbol} companyName={q.company_name} size={30} />
                      <div>
                        <Link
                          href={`/stocks/${q.symbol}`}
                          style={{ fontWeight: 700, color: "var(--clr-text)", textDecoration: "none" }}
                        >
                          {q.symbol}
                        </Link>
                        <div style={{ fontSize: 11, color: "var(--clr-text-muted)", marginTop: 1 }}>
                          {q.company_name}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="tabular-nums" style={{ padding: "12px 20px", textAlign: "right", fontWeight: 600 }}>
                    {q.current_price ? `$${Number(q.current_price).toFixed(2)}` : "—"}
                  </td>
                  <td
                    className={`tabular-nums ${isUp ? "positive" : isDown ? "negative" : ""}`}
                    style={{ padding: "12px 20px", textAlign: "right", fontWeight: 600 }}
                  >
                    {pct !== null ? (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 3, justifyContent: "flex-end" }}>
                        {isUp ? <TrendingUp size={12} /> : isDown ? <TrendingDown size={12} /> : <Minus size={12} />}
                        {isUp ? "+" : ""}{pct.toFixed(2)}%
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="tabular-nums" style={{ padding: "12px 20px", textAlign: "right", color: "var(--clr-text-muted)" }}>
                    {formatVolume(q.volume)}
                  </td>
                  <td style={{ padding: "12px 20px", textAlign: "right" }}>
                    {q.data_freshness === "NO_DATA" ? (
                      <span style={{ fontSize: 11, color: "var(--clr-text-faint)" }}>Gathering data…</span>
                    ) : (
                      <div style={{ display: "flex", justifyContent: "flex-end" }}>
                        <FreshnessIndicator freshness={q.data_freshness === "FRESH" ? "FRESH" : "STALE"} />
                      </div>
                    )}
                  </td>
                  <td style={{ padding: "12px 20px", textAlign: "right" }}>
                    {flagged && (
                      <span className="badge badge-high" style={{ fontSize: 10 }}>
                        <span className="badge-dot" /> Flagged
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
