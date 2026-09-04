"use client";

import { AreaChart, Area, ResponsiveContainer, YAxis } from "recharts";
import { useCandles } from "@/hooks/useCandles";

interface Props {
  symbol: string;
  isUp: boolean;
}

/** Small inline chart fed by real ingested snapshots — no synthetic data. */
export function Sparkline({ symbol, isUp }: Props) {
  const { data, isLoading } = useCandles(symbol, "1D");
  const points = data?.points ?? [];
  const resolvedColor = isUp ? "#15803d" : "#dc2626";

  if (isLoading) {
    return <div className="skeleton" style={{ height: 44, width: "100%" }} />;
  }

  if (points.length < 2) {
    return (
      <div
        style={{
          height: 44,
          display: "flex",
          alignItems: "center",
          fontSize: 11,
          color: "var(--clr-text-faint)",
        }}
      >
        Gathering intraday data…
      </div>
    );
  }

  const chartData = points.map((p) => ({ price: Number(p.price) }));
  const gradId = `spark-${symbol.replace(/[^a-zA-Z0-9]/g, "")}`;

  return (
    <div style={{ height: 44, width: "100%" }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 2, right: 0, bottom: 2, left: 0 }}>
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={resolvedColor} stopOpacity={0.25} />
              <stop offset="100%" stopColor={resolvedColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <YAxis hide domain={["dataMin", "dataMax"]} />
          <Area
            type="monotone"
            dataKey="price"
            stroke={resolvedColor}
            strokeWidth={1.75}
            fill={`url(#${gradId})`}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
