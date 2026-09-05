"use client";

import { motion } from "framer-motion";
import { ShieldCheck } from "lucide-react";

export function AllCaughtUp() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="card"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "56px 24px",
        textAlign: "center",
        gap: 16,
      }}
      id="all-caught-up-state"
    >
      <div
        style={{
          width: 52,
          height: 52,
          borderRadius: "50%",
          background: "var(--clr-green-bg)",
          border: "1px solid var(--clr-green-border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <ShieldCheck size={26} color="var(--clr-green)" />
      </div>

      <div style={{ maxWidth: 440 }}>
        <h2 style={{ fontSize: 20, fontWeight: 800, color: "#0f172a", letterSpacing: "-0.01em" }}>
          You&apos;re completely caught up
        </h2>
        <p style={{ color: "var(--clr-text-muted)", marginTop: 6, lineHeight: 1.6, fontSize: 13 }}>
          No abnormal price velocity, volume divergences, or unusual news catalysts since your last baseline.
          All tracked stocks are trading smoothly within standard bounds.
        </p>
      </div>

      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          fontSize: 12,
          color: "var(--clr-text-muted)",
          background: "var(--clr-surface-2)",
          padding: "4px 12px",
          borderRadius: 999,
          border: "1px solid var(--clr-border)",
        }}
      >
        <span className="pulse-dot" />
        <span>Continuous monitoring active</span>
      </div>
    </motion.div>
  );
}
