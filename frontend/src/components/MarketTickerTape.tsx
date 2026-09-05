"use client";

import { TrendingUp, TrendingDown } from "lucide-react";

interface TickerItem {
  symbol: string;
  name: string;
  value: string;
  changePct: number;
}

const DEFAULT_INDICES: TickerItem[] = [
  { symbol: "NIFTY 50", name: "NSE India", value: "25,481.20", changePct: 0.82 },
  { symbol: "SENSEX", name: "BSE India", value: "83,912.40", changePct: 0.71 },
  { symbol: "S&P 500", name: "US Large Cap", value: "5,864.67", changePct: 0.34 },
  { symbol: "NASDAQ", name: "Tech 100", value: "18,518.61", changePct: 0.62 },
  { symbol: "DOW", name: "Industrial", value: "42,352.75", changePct: 0.18 },
  { symbol: "BTC/USD", name: "Bitcoin", value: "$68,420", changePct: 1.85 },
  { symbol: "GOLD", name: "Spot Oz", value: "$2,735.20", changePct: 0.41 },
  { symbol: "CRUDE OIL", name: "WTI Barrel", value: "$74.38", changePct: -0.45 },
  { symbol: "10Y US", name: "Treasury", value: "4.18%", changePct: -0.02 },
];

export function MarketTickerTape() {
  const items = [...DEFAULT_INDICES, ...DEFAULT_INDICES];

  return (
    <div
      style={{
        width: "100%",
        overflow: "hidden",
        background: "#ffffff",
        borderBottom: "1px solid var(--clr-border)",
        height: 38,
        display: "flex",
        alignItems: "center",
        position: "relative",
        zIndex: 40,
      }}
    >
      {/* Live Badge indicator pinned to the left */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          padding: "0 16px",
          height: "100%",
          background: "linear-gradient(90deg, #ffffff 85%, rgba(255, 255, 255, 0) 100%)",
          zIndex: 2,
          flexShrink: 0,
          borderRight: "1px solid var(--clr-border)",
        }}
      >
        <span className="live-indicator-dot" />
        <span
          style={{
            fontSize: 10,
            fontWeight: 800,
            letterSpacing: "0.06em",
            color: "var(--clr-text-muted)",
            textTransform: "uppercase",
          }}
        >
          MARKETS
        </span>
      </div>

      {/* Marquee Content */}
      <div className="ticker-track">
        {items.map((item, index) => {
          const isUp = item.changePct >= 0;
          return (
            <div
              key={`${item.symbol}-${index}`}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                padding: "0 18px",
                fontSize: 12,
                whiteSpace: "nowrap",
                borderRight: "1px solid #f1f5f9",
              }}
            >
              <span style={{ fontWeight: 700, color: "var(--clr-text)" }}>{item.symbol}</span>
              <span className="tabular-nums" style={{ color: "var(--clr-text-muted)", fontSize: 11 }}>
                {item.value}
              </span>
              <span
                className={`tabular-nums ${isUp ? "positive" : "negative"}`}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 3,
                  fontSize: 11,
                  fontWeight: 700,
                  padding: "1px 6px",
                  borderRadius: 4,
                  background: isUp ? "var(--clr-green-bg)" : "var(--clr-red-bg)",
                }}
              >
                {isUp ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
                {isUp ? "+" : ""}
                {item.changePct.toFixed(2)}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
