"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useSpotlight } from "@/hooks/useSpotlight";

function useCountUp(target: number, duration = 500): number {
  const [value, setValue] = useState(target);
  useEffect(() => {
    const start = value;
    const diff = target - start;
    if (diff === 0) return;
    const startTime = performance.now();
    let raf: number;
    const tick = (now: number) => {
      const progress = Math.min(1, (now - startTime) / duration);
      setValue(Math.round(start + diff * progress));
      if (progress < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target]);
  return value;
}

export function AttentionSummary({
  critical,
  high,
  watch,
  total,
}: {
  critical: number;
  high: number;
  watch: number;
  total: number;
}) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, 1fr)",
        gap: 12,
        marginBottom: 24,
      }}
    >
      <StatCard value={total} label="Tracked Symbols" color="var(--clr-text)" />
      <StatCard value={critical} label="Critical" color="var(--clr-critical)" />
      <StatCard value={high} label="High" color="var(--clr-high)" />
      <StatCard value={watch} label="Watch" color="var(--clr-watch)" />
    </div>
  );
}

function StatCard({ value, label, color }: { value: number; label: string; color: string }) {
  const animated = useCountUp(value);
  const handleSpotlight = useSpotlight();
  return (
    <motion.div
      className="card spotlight tabular-nums"
      onMouseMove={handleSpotlight}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      style={{ textAlign: "center", padding: "16px 12px" }}
    >
      <div style={{ fontSize: 30, fontWeight: 800, color, lineHeight: 1 }}>{animated}</div>
      <div style={{ fontSize: 12, color: "var(--clr-text-muted)", marginTop: 4 }}>{label}</div>
    </motion.div>
  );
}
