"use client";

import { motion } from "framer-motion";

/**
 * Abstract candlestick + trend-line graphic for the auth hero — deliberately
 * generic (no ticker, no fabricated numbers) since this is a marketing
 * surface, not a data surface. Draws itself in once on mount rather than
 * looping, so it reads as a one-time flourish rather than a distraction.
 */
export function ChartMotif() {
  const bars = [
    { x: 10, h: 38, up: true },
    { x: 34, h: 58, up: true },
    { x: 58, h: 30, up: false },
    { x: 82, h: 70, up: true },
    { x: 106, h: 46, up: false },
    { x: 130, h: 86, up: true },
    { x: 154, h: 64, up: true },
  ];
  const baseY = 140;

  return (
    <svg
      viewBox="0 0 190 150"
      width="100%"
      height="auto"
      style={{ maxWidth: 340, overflow: "visible" }}
      aria-hidden="true"
    >
      {bars.map((bar, i) => (
        <motion.rect
          key={bar.x}
          x={bar.x}
          width={10}
          rx={2}
          fill={bar.up ? "currentColor" : "transparent"}
          stroke="currentColor"
          strokeOpacity={0.9}
          initial={{ y: baseY, height: 0, opacity: 0 }}
          animate={{ y: baseY - bar.h, height: bar.h, opacity: bar.up ? 0.85 : 0.4 }}
          transition={{ duration: 0.6, delay: 0.15 + i * 0.06, ease: "easeOut" }}
        />
      ))}
      <motion.path
        d="M 15 100 L 39 78 L 63 96 L 87 46 L 111 70 L 135 32 L 159 48"
        fill="none"
        stroke="var(--clr-accent)"
        strokeWidth={2.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={{ duration: 1.1, delay: 0.2, ease: "easeInOut" }}
      />
    </svg>
  );
}
