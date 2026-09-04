"use client";

import { motion } from "framer-motion";
import type { SignalBreakdown } from "@/lib/types";

interface Props {
  signals: SignalBreakdown;
}

const SIGNAL_LABELS: { key: keyof SignalBreakdown; label: string }[] = [
  { key: "price_move",    label: "Price Move" },
  { key: "volume_spike",  label: "Volume Spike" },
  { key: "relative_move", label: "vs Benchmark" },
  { key: "breakout",      label: "Breakout" },
  { key: "news_surge",    label: "News Surge" },
];

export function SignalBreakdownBars({ signals }: Props) {
  return (
    <div>
      <div
        style={{
          fontSize: 11,
          fontWeight: 700,
          color: "var(--clr-text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          marginBottom: 10,
        }}
      >
        Signal Breakdown
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
        {SIGNAL_LABELS.map(({ key, label }) => {
          const val = signals[key] ?? 0;
          const pct = Math.round(val * 100);
          return (
            <div key={key} style={{ display: "grid", gridTemplateColumns: "104px 1fr 36px", alignItems: "center", gap: 10 }}>
              <div style={{ fontSize: 12, color: "var(--clr-text-muted)" }}>{label}</div>
              <div className="signal-bar-track">
                <motion.div
                  className="signal-bar-fill"
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.6, ease: "easeOut" }}
                />
              </div>
              <div className="tabular-nums" style={{ fontSize: 11, color: "var(--clr-text-muted)", textAlign: "right" }}>{pct}%</div>
            </div>
          );
        })}
      </div>
      {signals.corroboration_boost > 0 && (
        <div style={{ marginTop: 8, fontSize: 11, color: "var(--clr-accent)", fontWeight: 600 }}>
          +{(signals.corroboration_boost * 100).toFixed(0)}% corroboration boost — multiple signals agree
        </div>
      )}
    </div>
  );
}

/**
 * Compact chip row used on AttentionCard. Every number here is real,
 * ingested data (or a ratio of two real numbers) — not derived from the
 * 0-1 normalized signal scores, which aren't precise enough to display as
 * if they were an actual multiplier or percentage.
 */
export function SignalChips({ priceChangePct, volume, avgVolume30d, benchmarkChangePct, newsCount }: {
  priceChangePct: number | null;
  volume: number | null;
  avgVolume30d: number | null;
  benchmarkChangePct: number | null;
  newsCount: number;
}) {
  const chips: string[] = [];
  if (priceChangePct !== null) {
    chips.push(`${priceChangePct >= 0 ? "+" : ""}${priceChangePct.toFixed(1)}% price move`);
  }
  if (volume && avgVolume30d && avgVolume30d > 0) {
    const ratio = volume / avgVolume30d;
    if (ratio >= 1.2) chips.push(`${ratio.toFixed(1)}× normal volume`);
  }
  if (priceChangePct !== null && benchmarkChangePct !== null) {
    const relative = priceChangePct - benchmarkChangePct;
    if (Math.abs(relative) >= 0.3) {
      chips.push(`${relative >= 0 ? "+" : ""}${relative.toFixed(1)}% vs benchmark`);
    }
  }
  if (newsCount > 0) {
    chips.push(newsCount === 1 ? "Relevant news detected" : `${newsCount} news items`);
  }

  if (chips.length === 0) return null;

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      {chips.map((c) => (
        <span key={c} className="chip">
          {c}
        </span>
      ))}
    </div>
  );
}
