"use client";

import { motion } from "framer-motion";
import { TrendingUp } from "lucide-react";
import { ChartMotif } from "./decor/ChartMotif";

const METRIC_CHIPS = [
  { label: "PRICE MOVE", value: "+7.8%", top: "8%", left: "4%", delay: 0 },
  { label: "VOLUME", value: "3.2× NORMAL", top: "62%", left: "2%", delay: 0.6 },
  { label: "NEWS SURGE", value: "DETECTED", top: "40%", left: "58%", delay: 1.2 },
];

/**
 * Shared left-column hero for /login and /signup. Illustrative only —
 * metric chips are generic labels, not a specific ticker's real-looking
 * numbers, so nothing here could be mistaken for fabricated live data.
 */
export function AuthHero() {
  return (
    <div className="auth-hero-col">
      <div className="auth-hero-dotgrid" />

      <div style={{ position: "relative", zIndex: 1 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 40 }}>
          <div
            style={{
              width: 34,
              height: 34,
              borderRadius: 10,
              background: "var(--clr-accent)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <TrendingUp size={18} color="#fff" />
          </div>
          <div style={{ fontWeight: 800, fontSize: 17 }}>Smart Watchlist</div>
        </div>

        <motion.h1
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          style={{ fontSize: 34, fontWeight: 800, lineHeight: 1.15, letterSpacing: "-0.02em", marginBottom: 14 }}
        >
          See what changed.
          <br />
          Know why it matters.
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.08 }}
          style={{ fontSize: 14, opacity: 0.72, maxWidth: 340, marginBottom: 44 }}
        >
          Every tracked stock scored on price, volume, relative move, and
          news — so you only see the moves that actually deserve your
          attention.
        </motion.p>

        <div style={{ position: "relative", height: 170 }}>
          <div style={{ color: "var(--clr-accent)", opacity: 0.9 }}>
            <ChartMotif />
          </div>

          {METRIC_CHIPS.map((chip) => (
            <motion.div
              key={chip.label}
              className="auth-metric-chip"
              style={{ top: chip.top, left: chip.left }}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: [0, -6, 0] }}
              transition={{
                opacity: { duration: 0.5, delay: 0.8 + chip.delay * 0.3 },
                y: { duration: 5, repeat: Infinity, ease: "easeInOut", delay: chip.delay },
              }}
            >
              <div style={{ opacity: 0.6, fontSize: 9 }}>{chip.label}</div>
              <div>{chip.value}</div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
