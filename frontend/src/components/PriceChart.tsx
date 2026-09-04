"use client";

import { useState } from "react";
import { AreaChart, Area, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { useCandles } from "@/hooks/useCandles";
import type { CandleRange } from "@/lib/types";

const RANGES: CandleRange[] = ["1D", "1W", "1M"];

function formatTick(iso: string, range: CandleRange): string {
  const d = new Date(iso);
  if (range === "1D") return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

interface Props {
  symbol: string;
}

export function PriceChart({ symbol }: Props) {
  const [range, setRange] = useState<CandleRange>("1W");
  const { data, isLoading } = useCandles(symbol, range);
  const points = data?.points ?? [];

  const prices = points.map((p) => Number(p.price));
  const isUp = prices.length >= 2 ? prices[prices.length - 1] >= prices[0] : true;
  const resolvedColor = isUp ? "#15803d" : "#dc2626";

  const chartData = points.map((p) => ({
    ts: p.timestamp,
    price: Number(p.price),
  }));

  return (
    <div className="card">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
        <h2 style={{ fontSize: 14, fontWeight: 700 }}>Price Chart</h2>
        <div style={{ display: "flex", gap: 4 }}>
          {RANGES.map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              id={`range-${r}`}
              style={{
                padding: "5px 12px",
                borderRadius: 999,
                fontSize: 12,
                fontWeight: 600,
                cursor: "pointer",
                border: "1px solid var(--clr-border)",
                background: range === r ? "var(--clr-text)" : "var(--clr-surface)",
                color: range === r ? "#fff" : "var(--clr-text-muted)",
                fontFamily: "inherit",
              }}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <div className="skeleton" style={{ height: 260, width: "100%" }} />}

      {!isLoading && points.length < 2 && (
        <div
          style={{
            height: 260,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--clr-text-faint)",
            fontSize: 13,
            textAlign: "center",
            padding: 24,
          }}
        >
          Not enough real data yet for this range. New symbols backfill 30 days of
          history in the background — check back shortly.
        </div>
      )}

      {!isLoading && points.length >= 2 && (
        <div style={{ height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="priceChartFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={resolvedColor} stopOpacity={0.22} />
                  <stop offset="100%" stopColor={resolvedColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--clr-border)" vertical={false} />
              <XAxis
                dataKey="ts"
                tickFormatter={(v) => formatTick(v, range)}
                tick={{ fontSize: 11, fill: "#7a7365" }}
                axisLine={{ stroke: "var(--clr-border)" }}
                tickLine={false}
                minTickGap={40}
              />
              <YAxis
                domain={["auto", "auto"]}
                tick={{ fontSize: 11, fill: "#7a7365" }}
                axisLine={false}
                tickLine={false}
                width={56}
                tickFormatter={(v) => `$${Number(v).toFixed(0)}`}
              />
              <Tooltip
                formatter={(value: number) => [`$${value.toFixed(2)}`, "Price"]}
                labelFormatter={(v) => new Date(v as string).toLocaleString()}
                contentStyle={{
                  background: "var(--clr-surface)",
                  border: "1px solid var(--clr-border)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Area
                type="monotone"
                dataKey="price"
                stroke={resolvedColor}
                strokeWidth={2}
                fill="url(#priceChartFill)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
