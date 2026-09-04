"use client";

import { useEffect, useState } from "react";

function relativeLabel(iso: string, now: number): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const diffSec = Math.max(0, Math.floor((now - then) / 1000));

  if (diffSec < 5) return "just now";
  if (diffSec < 60) return `${diffSec} sec ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin} min ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ${diffMin % 60}m ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

interface Props {
  iso: string | null | undefined;
  style?: React.CSSProperties;
  className?: string;
  fallback?: string;
}

/** Renders a "12 sec ago" label that ticks client-side, independent of refetch cadence. */
export function LiveTimestamp({ iso, style, className, fallback = "—" }: Props) {
  const [now, setNow] = useState<number | null>(null);

  useEffect(() => {
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  if (!iso || now === null) {
    return (
      <span style={style} className={className}>
        {fallback}
      </span>
    );
  }

  return (
    <span style={style} className={className}>
      {relativeLabel(iso, now)}
    </span>
  );
}
