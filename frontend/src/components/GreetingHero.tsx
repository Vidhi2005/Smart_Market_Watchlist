"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Layers, Clock } from "lucide-react";
import { LiveTimestamp } from "./LiveTimestamp";

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

interface Props {
  displayName: string;
  timezone: string;
  itemsCount: number;
  lastCheckedAt: string | null;
}

export function GreetingHero({ displayName, timezone, itemsCount, lastCheckedAt }: Props) {
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
        style={{
          marginTop: 20,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 16,
        }}
      >
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
      </motion.div>
    </div>
  );
}
