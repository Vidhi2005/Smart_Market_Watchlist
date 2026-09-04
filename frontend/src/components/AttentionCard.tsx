"use client";

import { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import type { AttentionItem } from "@/lib/types";
import { SignalBreakdownBars, SignalChips } from "./SignalBreakdown";
import { FreshnessIndicator } from "./FreshnessIndicator";
import { Sparkline } from "./Sparkline";
import { TrendingUp, TrendingDown, Newspaper, ChevronDown, Info, ExternalLink } from "lucide-react";
import { useSpotlight } from "@/hooks/useSpotlight";

interface AttentionCardProps {
  item: AttentionItem;
  index: number;
}

export function AttentionCard({ item, index }: AttentionCardProps) {
  const [expanded, setExpanded] = useState(false);
  const isUp = (item.price_change_pct ?? 0) >= 0;
  const level = item.attention_level;
  const handleSpotlight = useSpotlight();

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: Math.min(index, 6) * 0.06 }}
      whileHover={{ y: -2 }}
      onMouseMove={handleSpotlight}
      className={`card spotlight attention-card-${level}`}
      style={{ display: "grid", gap: 16 }}
      id={`attention-card-${item.symbol}`}
    >
      {/* ── Top row ── */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 26,
              height: 26,
              borderRadius: "50%",
              background: "var(--clr-surface-2)",
              border: "1px solid var(--clr-border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 12,
              fontWeight: 700,
              color: "var(--clr-text-muted)",
              flexShrink: 0,
            }}
          >
            {index + 1}
          </div>
          <div>
            <Link
              href={`/stocks/${item.symbol}`}
              style={{ fontWeight: 800, fontSize: 17, lineHeight: 1.2, color: "var(--clr-text)", textDecoration: "none" }}
            >
              {item.symbol}
            </Link>
            <div style={{ color: "var(--clr-text-muted)", fontSize: 12, marginTop: 2 }}>
              {item.company_name}
              {item.sector ? ` · ${item.sector}` : ""}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span
              title="Model confidence in this attention score, based on signal diversity and data freshness"
              style={{ display: "flex", alignItems: "center", gap: 3, fontSize: 11, color: "var(--clr-text-muted)" }}
            >
              Confidence {Math.round(item.confidence * 100)}% <Info size={11} />
            </span>
            <AttentionBadge level={level} />
          </div>
          <FreshnessIndicator freshness={item.data_freshness} detectedAt={item.detected_at} />
        </div>
      </div>

      {/* ── Price row ── */}
      {item.current_price && (
        <div style={{ display: "flex", alignItems: "center", gap: 16 }} className="tabular-nums">
          <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: "-0.03em" }}>
            ${Number(item.current_price).toFixed(2)}
          </div>
          <div
            className={isUp ? "positive" : "negative"}
            style={{ display: "flex", alignItems: "center", gap: 4, fontWeight: 700, fontSize: 15 }}
          >
            {isUp ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
            {isUp ? "+" : ""}{(item.price_change_pct ?? 0).toFixed(2)}%
          </div>
          {item.volume && (
            <div style={{ color: "var(--clr-text-muted)", fontSize: 12, marginLeft: "auto" }}>
              Vol: {formatVolume(item.volume)}
            </div>
          )}
        </div>
      )}

      {/* ── Real chips (only shown when backed by real numbers) ── */}
      <SignalChips
        priceChangePct={item.price_change_pct}
        volume={item.volume}
        avgVolume30d={item.avg_volume_30d}
        benchmarkChangePct={item.benchmark_change_pct}
        newsCount={item.latest_news.length}
      />

      {/* ── Why it matters ── */}
      <div>
        <div
          style={{
            fontSize: 11,
            fontWeight: 700,
            color: "var(--clr-text-muted)",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            marginBottom: 6,
          }}
        >
          Why it matters
        </div>
        <p style={{ fontSize: 14, lineHeight: 1.6, color: "var(--clr-text)" }}>
          {item.explanation}
          {item.explanation_source === "llm" && (
            <span
              style={{
                marginLeft: 8,
                fontSize: 10,
                color: "var(--clr-accent)",
                fontWeight: 700,
                verticalAlign: "middle",
              }}
            >
              AI
            </span>
          )}
        </p>
      </div>

      {/* ── Real intraday sparkline ── */}
      <Sparkline symbol={item.symbol} isUp={isUp} />

      {/* ── Expandable detail ── */}
      <button
        onClick={() => setExpanded((v) => !v)}
        id={`more-detail-${item.symbol}`}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          background: "none",
          border: "none",
          cursor: "pointer",
          fontSize: 12,
          fontWeight: 600,
          color: "var(--clr-text-muted)",
          padding: 0,
          fontFamily: "inherit",
          justifySelf: "start",
        }}
      >
        <ChevronDown size={14} style={{ transform: expanded ? "rotate(180deg)" : "none", transition: "transform 0.15s" }} />
        {expanded ? "Hide detail" : "More detail"}
      </button>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            style={{ overflow: "hidden" }}
          >
            <div style={{ display: "flex", flexDirection: "column", gap: 16, paddingTop: 4 }}>
              <SignalBreakdownBars signals={item.signals} />

              {item.latest_news.length > 0 && (
                <div>
                  <div
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      color: "var(--clr-text-muted)",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                      marginBottom: 8,
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                    }}
                  >
                    <Newspaper size={12} />
                    Recent News
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {item.latest_news.slice(0, 3).map((n) => (
                      <a
                        key={n.id}
                        href={n.url ?? "#"}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          fontSize: 12,
                          color: "var(--clr-text-muted)",
                          textDecoration: "none",
                          lineHeight: 1.4,
                        }}
                        onMouseOver={(e) => (e.currentTarget.style.color = "var(--clr-text)")}
                        onMouseOut={(e) => (e.currentTarget.style.color = "var(--clr-text-muted)")}
                      >
                        · {n.headline}
                      </a>
                    ))}
                  </div>
                </div>
              )}

              <Link
                href={`/stocks/${item.symbol}`}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 5,
                  fontSize: 12,
                  fontWeight: 600,
                  color: "var(--clr-accent)",
                  textDecoration: "none",
                  justifySelf: "start",
                }}
              >
                View full detail <ExternalLink size={11} />
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function AttentionBadge({ level }: { level: string }) {
  const cls =
    level === "CRITICAL" ? "badge-critical" :
    level === "HIGH"     ? "badge-high"     :
                           "badge-watch";
  return (
    <span className={`badge ${cls}`}>
      <span className="badge-dot" />
      {level}
    </span>
  );
}

function formatVolume(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000)     return `${(v / 1_000).toFixed(0)}K`;
  return String(v);
}
