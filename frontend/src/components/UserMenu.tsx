"use client";

import { useEffect, useRef, useState } from "react";
import { LogOut, ChevronDown } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function UserMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  if (!user) return null;

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        onClick={() => setOpen((v) => !v)}
        id="user-menu-trigger"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          background: "none",
          border: "none",
          cursor: "pointer",
          padding: "4px 6px 4px 4px",
          borderRadius: 999,
          fontFamily: "inherit",
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            background: "var(--clr-accent)",
            color: "#fff",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 12,
            fontWeight: 700,
            flexShrink: 0,
          }}
        >
          {initials(user.display_name)}
        </div>
        <ChevronDown size={14} color="var(--clr-text-muted)" />
      </button>

      {open && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 8px)",
            right: 0,
            minWidth: 190,
            background: "var(--clr-surface)",
            border: "1px solid var(--clr-border)",
            borderRadius: "var(--radius-md)",
            boxShadow: "var(--shadow-pop)",
            overflow: "hidden",
            zIndex: 100,
          }}
        >
          <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--clr-border)" }}>
            <div style={{ fontWeight: 700, fontSize: 13 }}>{user.display_name}</div>
            <div style={{ fontSize: 11, color: "var(--clr-text-muted)", marginTop: 2 }}>{user.email}</div>
          </div>
          <button
            onClick={logout}
            id="logout-btn"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              width: "100%",
              padding: "10px 14px",
              background: "none",
              border: "none",
              cursor: "pointer",
              fontSize: 13,
              color: "var(--clr-red)",
              fontFamily: "inherit",
              textAlign: "left",
            }}
            onMouseOver={(e) => (e.currentTarget.style.background = "var(--clr-surface-2)")}
            onMouseOut={(e) => (e.currentTarget.style.background = "none")}
          >
            <LogOut size={14} /> Log out
          </button>
        </div>
      )}
    </div>
  );
}
