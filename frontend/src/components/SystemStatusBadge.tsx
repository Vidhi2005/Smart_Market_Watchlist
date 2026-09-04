"use client";

import { useHealth } from "@/hooks/useHealth";

export function SystemStatusBadge() {
  const { data, isError, isLoading } = useHealth();

  const ok = !isError && !isLoading && data?.status === "ok";
  const label = isLoading
    ? "Checking systems…"
    : ok
    ? "All systems operational"
    : "Backend unreachable";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        fontSize: 11,
        color: ok ? "var(--clr-text-muted)" : "var(--clr-red)",
        fontWeight: 500,
      }}
      title={data ? `API v${data.version} · DB: ${data.db}` : undefined}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: isLoading ? "var(--clr-text-faint)" : ok ? "var(--clr-green)" : "var(--clr-red)",
          display: "inline-block",
        }}
      />
      {label}
    </div>
  );
}
