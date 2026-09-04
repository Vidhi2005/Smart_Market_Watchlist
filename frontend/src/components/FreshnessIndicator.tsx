"use client";

import { LiveTimestamp } from "./LiveTimestamp";

interface Props {
  freshness: "FRESH" | "STALE";
  detectedAt?: string;
}

export function FreshnessIndicator({ freshness, detectedAt }: Props) {
  const isFresh = freshness === "FRESH";
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 5,
        fontSize: 11,
        color: isFresh ? "var(--clr-green)" : "var(--clr-text-muted)",
        fontWeight: 600,
      }}
    >
      {isFresh ? (
        <span className="pulse-dot" style={{ width: 5, height: 5 }} />
      ) : (
        <span
          style={{
            width: 5,
            height: 5,
            borderRadius: "50%",
            background: "var(--clr-text-faint)",
            display: "inline-block",
          }}
        />
      )}
      {isFresh ? "Fresh" : "Delayed"}
      {detectedAt && (
        <>
          <span style={{ color: "var(--clr-text-faint)" }}>·</span>
          <LiveTimestamp iso={detectedAt} style={{ fontWeight: 500, color: "var(--clr-text-muted)" }} />
        </>
      )}
    </div>
  );
}
