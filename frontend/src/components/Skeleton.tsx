"use client";

export function Skeleton({ width = "100%", height = 16, style }: {
  width?: string | number;
  height?: string | number;
  style?: React.CSSProperties;
}) {
  return (
    <div
      className="skeleton"
      style={{ width, height, ...style }}
    />
  );
}

export function CardSkeleton() {
  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <Skeleton width={44} height={44} style={{ borderRadius: 10 }} />
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
          <Skeleton width="40%" height={18} />
          <Skeleton width="60%" height={12} />
        </div>
      </div>
      <Skeleton width="100%" height={14} />
      <Skeleton width="80%" height={14} />
      <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
        {[...Array(5)].map((_, i) => (
          <div key={i} style={{ display: "grid", gridTemplateColumns: "100px 1fr 36px", gap: 10, alignItems: "center" }}>
            <Skeleton height={10} />
            <Skeleton height={6} style={{ borderRadius: 3 }} />
            <Skeleton height={10} width={28} />
          </div>
        ))}
      </div>
    </div>
  );
}
