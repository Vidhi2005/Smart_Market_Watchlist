"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Layers, Clock, ArrowRight } from "lucide-react";
import { LiveTimestamp } from "./LiveTimestamp";
import type { AttentionItem } from "@/lib/types";

/**
 * Time-of-day in a specific IANA timezone — NOT the executing machine's
 * local clock. Computing this from `new Date().getHours()` was the bug:
 * that reflects wherever the code runs (the server, during Next's static
 * prerender of "/"), not the visitor's actual time, so everyone saw
 * whatever greeting was baked in at build time regardless of their real
 * timezone.
 */
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
  const h = hourInTimezone(timezone);
  // A plain "h < 12 → morning" bucket is wrong for the hours that actually
  // matter most here — 2am was landing in "morning" just because 2 < 12.
  if (h < 5) return "night";
  if (h < 12) return "morning";
  if (h < 17) return "afternoon";
  if (h < 21) return "evening";
  return "night";
}

function firstName(displayName: string): string {
  return displayName.trim().split(/\s+/)[0] || displayName;
}

function levelColor(level: string): string {
  if (level === "CRITICAL") return "var(--clr-critical)";
  if (level === "HIGH") return "var(--clr-high)";
  return "var(--clr-watch)";
}

interface Props {
  displayName: string;
  timezone: string;
  items: AttentionItem[];
  lastCheckedAt: string | null;
}

export function GreetingHero({ displayName, timezone, items, lastCheckedAt }: Props) {
  const itemsCount = items.length;
  const preview = items.slice(0, 3);
  // Computed client-side only, after mount — same pattern as LiveTimestamp —
  // so the greeting is never baked into server-rendered/static HTML using
  // the wrong clock, and re-checks periodically for long-lived tabs.
  const [greeting, setGreeting] = useState<string | null>(null);

  useEffect(() => {
    const update = () => setGreeting(timeGreeting(timezone));
    update();
    const id = setInterval(update, 60_000);
    return () => clearInterval(id);
  }, [timezone]);

  return (
    <div style={{ marginBottom: 24 }}>
      <motion.h1
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        style={{ fontSize: 26, fontWeight: 800, letterSpacing: "-0.02em" }}
      >
        <span className="gradient-text">Good {greeting ?? "day"}, {firstName(displayName)}</span>{" "}
        <span style={{ display: "inline-block" }}>👋</span>
      </motion.h1>
      <motion.p
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.05 }}
        style={{ color: "var(--clr-text-muted)", marginTop: 4, fontSize: 14 }}
      >
        Here&apos;s what changed since you last checked.
      </motion.p>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.1 }}
        className={`card${itemsCount > 0 ? " glow-alert" : ""}`}
        style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 16 }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div
              style={{
                width: 42,
                height: 42,
                borderRadius: 11,
                background: "var(--clr-accent-bg)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <Layers size={19} color="var(--clr-accent)" />
            </div>
            <div>
              <div style={{ fontSize: 11, color: "var(--clr-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>
                Since you last checked
              </div>
              <div style={{ fontSize: 18, fontWeight: 700, marginTop: 2 }}>
                {itemsCount > 0
                  ? `${itemsCount} thing${itemsCount > 1 ? "s" : ""} deserve${itemsCount > 1 ? "" : "s"} your attention`
                  : "Nothing needs your attention right now"}
              </div>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--clr-text-muted)", flexShrink: 0 }}>
            <Clock size={13} />
            {lastCheckedAt ? (
              <>
                Last checked <LiveTimestamp iso={lastCheckedAt} />
              </>
            ) : (
              "First visit"
            )}
          </div>
        </div>

        {preview.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8, paddingTop: 4, borderTop: "1px solid var(--clr-border)" }}>
            {preview.map((item) => (
              <div key={item.symbol} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13 }}>
                <span className="badge-dot" style={{ background: levelColor(item.attention_level) }} />
                <span style={{ fontWeight: 700, minWidth: 56 }}>{item.symbol}</span>
                {item.price_change_pct !== null && (
                  <span className={item.price_change_pct >= 0 ? "positive" : "negative"} style={{ fontWeight: 600, minWidth: 60 }}>
                    {item.price_change_pct >= 0 ? "+" : ""}{item.price_change_pct.toFixed(1)}%
                  </span>
                )}
                <span style={{ color: levelColor(item.attention_level), fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  {item.attention_level}
                </span>
              </div>
            ))}
            <a
              href="#attention-list"
              style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 12, fontWeight: 600, color: "var(--clr-accent)", textDecoration: "none", marginTop: 2 }}
            >
              View all <ArrowRight size={12} />
            </a>
          </div>
        )}
      </motion.div>
    </div>
  );
}
