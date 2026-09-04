"use client";

interface Props {
  label: string;
  isOpen: boolean;
}

export function MarketStatusPill({ label, isOpen }: Props) {
  return (
    <div className="chip" style={{ color: isOpen ? "var(--clr-green)" : "var(--clr-text-muted)" }}>
      {isOpen ? (
        <span className="pulse-dot" />
      ) : (
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: "var(--clr-text-faint)",
            display: "inline-block",
          }}
        />
      )}
      {label} {isOpen ? "Open" : "Closed"}
    </div>
  );
}
