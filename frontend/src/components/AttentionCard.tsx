"use client";

import { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import type { AttentionItem } from "@/lib/types";
import { SignalBreakdownBars, SignalChips } from "./SignalBreakdown";
import { StockAvatar } from "./StockAvatar";
import { FreshnessIndicator } from "./FreshnessIndicator";
import { Sparkline } from "./Sparkline";
import { TrendingUp, TrendingDown, Newspaper, ChevronDown, Info, ExternalLink, Check } from "lucide-react";
import { useSpotlight } from "@/hooks/useSpotlight";

interface AttentionCardProps {
  item: AttentionItem;
  index: number;
  onMarkReviewed?: (symbolId: string) => void;
  isMarking?: boolean;
}

export function AttentionCard({ item, index, onMarkReviewed, isMarking }: AttentionCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [justReviewed, setJustReviewed] = useState(false);
  const hasSinceChecked = item.since_checked_change_pct !== null;
  const primaryPct = hasSinceChecked ? item.since_checked_change_pct! : (item.price_change_pct ?? 0);
  const isUp = primaryPct >= 0;
  const level = item.attention_level;
  const handleSpotlight = useSpotlight();

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.25, delay: Math.min(index, 6) * 0.05 }}
      whileHover={{ y: -2 }}
      onMouseMove={handleSpotlight}
      className={`card spotlight attention-card-${level}`}
      style={{ display: "grid", gap: 16 }}
      id={`attention-card-${item.symbol}`}
    >
      {/* ── Top row ── */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <StockAvatar symbol={item.symbol} companyName={item.company_name} size={38} />
          <div>
            <Link
              href={`/stocks/${item.symbol}`}
              style={{ fontWeight: 800, fontSize: 18, lineHeight: 1.2, color: "var(--clr-text)", textDecoration: "none" }}
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
        <div style={{ background: "#f8fafc", padding: "12px 16px", borderRadius: "var(--radius-sm)", border: "1px solid var(--clr-border)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }} className="tabular-nums">
            <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: "-0.03em", color: "#0f172a" }}>
              ${Number(item.current_price).toFixed(2)}
            </div>
            <div
              className={isUp ? "positive" : "negative"}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
                fontWeight: 700,
                fontSize: 14,
                padding: "2px 8px",
                borderRadius: 6,
                background: isUp ? "var(--clr-green-bg)" : "var(--clr-red-bg)",
              }}
              title={hasSinceChecked ? "Move since you last checked this stock" : "Today's move vs previous close"}
            >
              {isUp ? <TrendingUp size={15} /> : <TrendingDown size={15} />}
              {isUp ? "+" : ""}{primaryPct.toFixed(2)}%
            </div>
            {item.volume && (
              <div style={{ color: "var(--clr-text-muted)", fontSize: 12, marginLeft: "auto", fontWeight: 500 }}>
                Vol: {formatVolume(item.volume)}
              </div>
            )}
          </div>
          <div style={{ fontSize: 11, color: "var(--clr-text-faint)", marginTop: 4 }}>
            {hasSinceChecked ? (
              <>Since you checked · Today {(item.price_change_pct ?? 0) >= 0 ? "+" : ""}{(item.price_change_pct ?? 0).toFixed(2)}%</>
            ) : (
              "Today's move — no prior baseline yet"
            )}
          </div>
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
      <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "var(--radius-sm)", border: "1px solid #e2e8f0" }}>
        <div
          style={{
            fontSize: 11,
            fontWeight: 800,
            color: "var(--clr-text-muted)",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            marginBottom: 6,
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          Why it matters
          {item.explanation_source === "llm" && (
            <span
              style={{
                marginLeft: "auto",
                fontSize: 10,
                color: "var(--clr-accent)",
                background: "rgba(16, 185, 129, 0.12)",
                padding: "1px 6px",
                borderRadius: 4,
                fontWeight: 700,
              }}
            >
              AI SYNTHESIS
            </span>
          )}
        </div>
        <p style={{ fontSize: 13, lineHeight: 1.6, color: "var(--clr-text)" }}>
          {item.explanation}
        </p>
      </div>

      {/* ── Real intraday sparkline ── */}
      <Sparkline symbol={item.symbol} isUp={isUp} />

      {/* ── Expandable detail + review action ── */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
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
          }}
        >
          <ChevronDown size={14} style={{ transform: expanded ? "rotate(180deg)" : "none", transition: "transform 0.15s" }} />
          {expanded ? "Hide detail" : "More detail"}
        </button>

        {onMarkReviewed && (
          <button
            onClick={() => {
              setJustReviewed(true);
              onMarkReviewed(item.symbol_id);
            }}
            disabled={justReviewed || isMarking}
            id={`mark-reviewed-${item.symbol}`}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 5,
              background: "none",
              border: "none",
              cursor: justReviewed ? "default" : "pointer",
              fontSize: 11,
              fontWeight: 600,
              color: "var(--clr-text-faint)",
              padding: 0,
              fontFamily: "inherit",
              opacity: justReviewed ? 0.7 : 1,
            }}
          >
            <Check size={12} />
            {justReviewed ? "Reviewed just now" : "Mark reviewed"}
          </button>
        )}
      </div>

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
