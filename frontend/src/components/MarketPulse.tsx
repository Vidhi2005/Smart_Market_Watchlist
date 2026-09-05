"use client";

import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2 } from "lucide-react";
import type { AttentionItem, QuoteOut } from "@/lib/types";
import { StockAvatar } from "./StockAvatar";

interface Props {
  items: AttentionItem[];
  quotes: QuoteOut[];
}

type Level = "CRITICAL" | "HIGH" | "WATCH" | "QUIET";

const LANES: { level: Level; label: string; color: string }[] = [
  { level: "CRITICAL", label: "Critical", color: "var(--clr-critical)" },
  { level: "HIGH", label: "High", color: "var(--clr-high)" },
  { level: "WATCH", label: "Watch", color: "var(--clr-watch)" },
  { level: "QUIET", label: "Quiet", color: "var(--clr-text-faint)" },
];

/**
 * An at-a-glance strip of EVERY tracked symbol, grouped into labeled lanes
 * by attention level — position and text label carry the meaning, not just
 * color, so it's still readable without color vision. Complements (doesn't
 * replace) the detailed card list below it.
 */
export function MarketPulse({ items, quotes }: Props) {
  if (quotes.length === 0) return null;

  const flaggedBySymbol = new Map(items.map((i) => [i.symbol, i]));

  const lanes = LANES.map((lane) => ({
    ...lane,
    symbols: quotes
      .map((q) => {
        const flagged = flaggedBySymbol.get(q.symbol);
        const level: Level = (flagged?.attention_level as Level) ?? "QUIET";
        const pct = flagged ? flagged.price_change_pct : q.price_change_pct;
        return { symbol: q.symbol, companyName: q.company_name, level, pct };
      })
      .filter((s) => s.level === lane.level),
  }));

  return (
    <div className="card" style={{ marginBottom: 20 }}>
      <div
        style={{
          fontSize: 11,
          fontWeight: 700,
          color: "var(--clr-text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          marginBottom: 2,
        }}
      >
        Market Pulse
      </div>
      <div style={{ fontSize: 12, color: "var(--clr-text-faint)", marginBottom: 18 }}>
        Your watchlist, at a glance
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
          gap: 20,
        }}
      >
        {lanes.map((lane) => (
          <div key={lane.level}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 11,
                fontWeight: 700,
                color: lane.color,
                textTransform: "uppercase",
                letterSpacing: "0.04em",
                marginBottom: 10,
                paddingBottom: 8,
                borderBottom: "1px solid var(--clr-border)",
              }}
            >
              <span className="badge-dot" style={{ background: lane.color }} />
              {lane.label} · {lane.symbols.length}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, minHeight: 20 }}>
              <AnimatePresence initial={false}>
                {lane.symbols.length === 0 ? (
                  <motion.div
                    key="empty"
                    layout
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--clr-text-faint)" }}
                  >
                    <CheckCircle2 size={13} /> All quiet
                  </motion.div>
                ) : (
                  lane.symbols.map(({ symbol, companyName, pct }) => (
                    // layoutId shared across lanes: when a symbol's level
                    // changes between polls, it visibly travels from its old
                    // lane to its new one instead of just popping — the
                    // motion itself shows the product doing its job.
                    <motion.div
                      key={symbol}
                      layoutId={`pulse-${symbol}`}
                      layout
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.9 }}
                      transition={{ layout: { type: "spring", stiffness: 300, damping: 28 }, opacity: { duration: 0.2 } }}
                      style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, fontSize: 12 }}
                    >
                      <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <StockAvatar symbol={symbol} companyName={companyName} size={18} />
                        <span style={{ fontWeight: 700 }}>{symbol}</span>
                      </span>
                      {pct !== null && (
                        <span className={pct >= 0 ? "positive" : "negative"} style={{ fontSize: 11, fontWeight: 600 }}>
                          {pct >= 0 ? "+" : ""}{pct.toFixed(1)}%
                        </span>
                      )}
                    </motion.div>
                  ))
                )}
              </AnimatePresence>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
