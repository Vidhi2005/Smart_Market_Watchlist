"use client";

// A fixed palette, not random colors — same symbol always gets the same
// color across every render/page, which is what makes it feel like a real
// identity mark rather than decoration.
const PALETTE = [
  "#f97316", "#16a34a", "#2563eb", "#dc2626", "#9333ea",
  "#0891b2", "#ca8a04", "#db2777", "#059669", "#4f46e5",
];

function colorForSymbol(symbol: string): string {
  let hash = 0;
  for (let i = 0; i < symbol.length; i++) hash = symbol.charCodeAt(i) + ((hash << 5) - hash);
  return PALETTE[Math.abs(hash) % PALETTE.length];
}

function initials(companyName: string, symbol: string): string {
  const words = companyName.trim().split(/\s+/).filter(Boolean);
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return symbol.slice(0, 2).toUpperCase();
}

interface Props {
  symbol: string;
  companyName: string;
  size?: number;
}

/** Deterministic colored initials avatar — real company data, no image assets. */
export function StockAvatar({ symbol, companyName, size = 36 }: Props) {
  const color = colorForSymbol(symbol);
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: color,
        color: "#fff",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: Math.round(size * 0.36),
        fontWeight: 800,
        letterSpacing: "-0.02em",
        flexShrink: 0,
      }}
    >
      {initials(companyName, symbol)}
    </div>
  );
}
