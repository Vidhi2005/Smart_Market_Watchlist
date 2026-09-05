"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ArrowDown, Clock, ShieldCheck, TrendingUp, TrendingDown, Layers } from "lucide-react";
import { LiveTimestamp } from "./LiveTimestamp";
import { ChartMotif } from "./decor/ChartMotif";
import type { AttentionItem } from "@/lib/types";

function hourInTimezone(timezone: string): number {
  try {
    const parts = new Intl.DateTimeFormat("en-US", {
      hour: "numeric",
      hour12: false,
      timeZone: timezone,
    }).formatToParts(new Date());
    const hour = parts.find((p) => p.type === "hour")?.value;
    return hour ? parseInt(hour, 10) % 24 : new Date().getHours();
  } catch {
    return new Date().getHours();
  }
}

function timeGreeting(timezone: string): string {
  // No "night" bucket — "Good night" reads as a farewell/sign-off, not a
  // welcome, so late hours (and the pre-dawn hours) fall back to "evening"
  // and "morning" respectively instead.
  const h = hourInTimezone(timezone);
  if (h < 5) return "evening";
  if (h < 12) return "morning";
  if (h < 17) return "afternoon";
  return "evening";
}

function firstName(displayName: string): string {
  return displayName.trim().split(/\s+/)[0] || displayName;
}

interface Props {
  displayName: string;
  timezone: string;
  items: AttentionItem[];
  lastCheckedAt: string | null;
}

export function GreetingHero({ displayName, timezone, items, lastCheckedAt }: Props) {
  const itemsCount = items.length;
  const urgentCount = items.filter((i) => i.attention_level === "CRITICAL" || i.attention_level === "HIGH").length;
  const [greeting, setGreeting] = useState<string | null>(null);

  useEffect(() => {
    const update = () => setGreeting(timeGreeting(timezone));
    update();
    const id = setInterval(update, 60_000);
    return () => clearInterval(id);
  }, [timezone]);

  return (
    <div style={{ marginBottom: 24 }}>
      {/* Top Header Row */}
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: "#0f172a", letterSpacing: "-0.02em" }}>
            Good {greeting ?? "day"}, {firstName(displayName)} 👋
          </h1>
          <p style={{ color: "var(--clr-text-muted)", marginTop: 2, fontSize: 13 }}>
            Continuous market observation layer — tracking velocity, volume anomalies, and news.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--clr-text-muted)" }}>
          <Clock size={13} />
          {lastCheckedAt ? (
            <>
              Baseline since <LiveTimestamp iso={lastCheckedAt} />
            </>
          ) : (
            "First visit"
          )}
        </div>
      </div>

      {/* Market Intelligence Core Banner (Emerald Fintech Briefing) */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        style={{
          background: "linear-gradient(135deg, #047857 0%, #059669 50%, #10b981 100%)",
          borderRadius: "var(--radius-md)",
          padding: "24px 28px",
          color: "#ffffff",
          boxShadow: "0 4px 20px rgba(5, 150, 105, 0.18)",
          position: "relative",
          overflow: "hidden",
          display: "grid",
          gridTemplateColumns: "1fr auto",
          gap: 24,
          alignItems: "center",
        }}
      >
        <div style={{ position: "relative", zIndex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <span
              style={{
                fontSize: 10,
                fontWeight: 800,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                background: "rgba(255, 255, 255, 0.2)",
                padding: "3px 8px",
                borderRadius: 4,
              }}
            >
              MARKET INTELLIGENCE
            </span>
            <span style={{ fontSize: 12, opacity: 0.85, fontWeight: 600 }}>
              SINCE YOU LAST CHECKED
            </span>
          </div>

          <h2 style={{ fontSize: 22, fontWeight: 800, lineHeight: 1.25, letterSpacing: "-0.01em", marginBottom: 12 }}>
            {itemsCount > 0
              ? `${itemsCount} market move${itemsCount > 1 ? "s" : ""} detected · ${urgentCount} require${urgentCount === 1 ? "s" : ""} your attention`
              : "No significant changes since you last visited — all positions quiet"}
          </h2>

          {/* Dynamic real ticker chips from actual items data */}
          {itemsCount > 0 ? (
            <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 10, marginTop: 14 }}>
              {items.slice(0, 4).map((item) => {
                const isUp = (item.price_change_pct ?? 0) >= 0;
                const volumeMultiple = item.avg_volume_30d && item.volume
                  ? (item.volume / item.avg_volume_30d).toFixed(1)
                  : null;

                return (
                  <div
                    key={item.symbol}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                      background: "rgba(0, 0, 0, 0.22)",
                      backdropFilter: "blur(4px)",
                      border: "1px solid rgba(255, 255, 255, 0.2)",
                      padding: "4px 10px",
                      borderRadius: 6,
                      fontSize: 12,
                      fontWeight: 600,
                    }}
                  >
                    <span style={{ fontWeight: 800 }}>{item.symbol}</span>
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 2,
                        color: isUp ? "#a7f3d0" : "#fca5a5",
                      }}
                    >
                      {isUp ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                      {isUp ? "+" : ""}{(item.price_change_pct ?? 0).toFixed(1)}%
                    </span>
                    {volumeMultiple && parseFloat(volumeMultiple) >= 1.5 && (
                      <span style={{ fontSize: 11, opacity: 0.8 }}>· {volumeMultiple}× vol</span>
                    )}
                  </div>
                );
              })}

              <a
                href="#attention-list"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 4,
                  fontSize: 12,
                  fontWeight: 700,
                  color: "#ffffff",
                  textDecoration: "underline",
                  textUnderlineOffset: "3px",
                  marginLeft: 4,
                }}
              >
                View attention cards <ArrowDown size={13} />
              </a>
            </div>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, opacity: 0.9 }}>
              <ShieldCheck size={16} />
              <span>All tracked stocks trading within normal baseline bands.</span>
            </div>
          )}
        </div>

        {/* Product-Native SVG Chart Motif on the right */}
        <div
          style={{
            position: "relative",
            zIndex: 1,
            width: 140,
            opacity: 0.35,
            color: "#ffffff",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <ChartMotif />
        </div>
      </motion.div>
    </div>
  );
}
