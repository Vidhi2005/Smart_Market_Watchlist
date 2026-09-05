"use client";

import { Activity, AlertCircle, AlertTriangle, Eye } from "lucide-react";

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
        gap: 14,
        marginBottom: 24,
      }}
    >
      <StatCard
        value={total}
        label="Tracked Symbols"
        color="#0f172a"
        accentColor="#94a3b8"
        icon={<Activity size={16} />}
      />
      <StatCard
        value={critical}
        label="Critical Attention"
        color="var(--clr-critical)"
        accentColor="var(--clr-critical)"
        icon={<AlertCircle size={16} />}
      />
      <StatCard
        value={high}
        label="High Priority"
        color="var(--clr-high)"
        accentColor="var(--clr-high)"
        icon={<AlertTriangle size={16} />}
      />
      <StatCard
        value={watch}
        label="Watch List"
        color="var(--clr-watch)"
        accentColor="var(--clr-watch)"
        icon={<Eye size={16} />}
      />
    </div>
  );
}

function StatCard({
  value,
  label,
  color,
  accentColor,
  icon,
}: {
  value: number;
  label: string;
  color: string;
  accentColor: string;
  icon: React.ReactNode;
}) {
  return (
    <div
      className="card tabular-nums"
      style={{
        padding: "16px 18px",
        position: "relative",
        overflow: "hidden",
        borderTop: `3px solid ${accentColor}`,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: "var(--clr-text-muted)" }}>{label}</span>
        <span style={{ color: accentColor, opacity: 0.85 }}>{icon}</span>
      </div>
      <div
        style={{
          fontSize: 28,
          fontWeight: 800,
          color,
          lineHeight: 1,
          letterSpacing: "-0.02em",
        }}
      >
        {value}
      </div>
    </div>
  );
}
