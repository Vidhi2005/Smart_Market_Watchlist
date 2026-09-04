"use client";

import { motion } from "framer-motion";
import { CheckCircle2 } from "lucide-react";

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
        padding: "72px 24px",
        textAlign: "center",
        gap: 14,
      }}
      id="all-caught-up-state"
    >
      <div
        style={{
          width: 56,
          height: 56,
          borderRadius: "50%",
          background: "var(--clr-accent-bg)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <CheckCircle2 size={28} color="var(--clr-accent)" />
      </div>
      <h2 style={{ fontSize: 22, fontWeight: 800 }}>You&apos;re all caught up</h2>
      <p style={{ color: "var(--clr-text-muted)", maxWidth: 380, lineHeight: 1.6, fontSize: 14 }}>
        No significant changes since you last checked your watchlist. We&apos;ll surface
        something here the moment it&apos;s worth your attention.
      </p>
      <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--clr-text-faint)" }}>
        <span className="pulse-dot" style={{ background: "var(--clr-accent)" }} />
        Watching in the background
      </div>
    </motion.div>
  );
}
