"use client";

import { motion } from "framer-motion";
import { TrendingUp } from "lucide-react";
import { ChartMotif } from "./decor/ChartMotif";

const METRIC_CHIPS = [
  { label: "PRICE MOVE", value: "+7.8%", top: "10%", left: "4%", delay: 0 },
  { label: "VOLUME", value: "3.2× NORMAL", top: "64%", left: "2%", delay: 0.6 },
  { label: "NEWS CATALYST", value: "DETECTED", top: "42%", left: "56%", delay: 1.2 },
];

export function AuthHero() {
  return (
    <div className="auth-hero-col">
      <div className="auth-hero-dotgrid" />

      <div style={{ position: "relative", zIndex: 1 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 36 }}>
          <div
            style={{
              width: 34,
              height: 34,
              borderRadius: 8,
              background: "var(--clr-accent)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <TrendingUp size={18} color="#ffffff" strokeWidth={2.5} />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 17, color: "#ffffff" }}>Smart Watchlist</div>
            <div style={{ fontSize: 10, fontWeight: 700, color: "var(--clr-accent-light)", letterSpacing: "0.05em", textTransform: "uppercase" }}>
              Attention Engine
            </div>
          </div>
        </div>

        <motion.h1
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
          style={{ fontSize: 32, fontWeight: 800, lineHeight: 1.2, letterSpacing: "-0.02em", marginBottom: 12, color: "#ffffff" }}
        >
          See what changed.
          <br />
          <span style={{ color: "var(--clr-accent-light)" }}>Know why it matters.</span>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.08 }}
          style={{ fontSize: 14, opacity: 0.78, maxWidth: 340, marginBottom: 36, lineHeight: 1.6 }}
        >
          Every tracked stock continuously scored on price velocity, volume anomalies,
          and breaking news — surfacing only the moves that genuinely deserve your focus.
        </motion.p>

        <div style={{ position: "relative", height: 180 }}>
          <div style={{ color: "var(--clr-accent-light)", opacity: 0.85 }}>
            <ChartMotif />
          </div>

          {METRIC_CHIPS.map((chip) => (
            <motion.div
              key={chip.label}
              className="auth-metric-chip"
              style={{ top: chip.top, left: chip.left }}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: [0, -4, 0] }}
              transition={{
                opacity: { duration: 0.5, delay: 0.6 + chip.delay * 0.2 },
                y: { duration: 4.5, repeat: Infinity, ease: "easeInOut", delay: chip.delay },
              }}
            >
              <div style={{ opacity: 0.6, fontSize: 9 }}>{chip.label}</div>
              <div style={{ fontWeight: 800, marginTop: 1 }}>{chip.value}</div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
