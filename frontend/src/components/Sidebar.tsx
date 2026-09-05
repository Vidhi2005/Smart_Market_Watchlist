"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { LayoutGrid, ListChecks, Settings, ChevronLeft, ChevronRight, TrendingUp, Sparkles } from "lucide-react";

interface NavItemProps {
  href: string;
  icon: React.ReactNode;
  label: string;
  active: boolean;
  collapsed: boolean;
}

function NavItem({ href, icon, label, active, collapsed }: NavItemProps) {
  return (
    <Link
      href={href}
      title={label}
      style={{
        position: "relative",
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "10px 12px",
        borderRadius: "var(--radius-sm)",
        fontSize: 13,
        fontWeight: active ? 700 : 500,
        color: active ? "#0f172a" : "var(--clr-text-muted)",
        textDecoration: "none",
        transition: "color 0.15s ease",
      }}
    >
      {active && (
        <motion.div
          layoutId="nav-active-indicator"
          transition={{ type: "spring", stiffness: 380, damping: 32 }}
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "var(--radius-sm)",
            background: "rgba(16, 185, 129, 0.08)",
            borderLeft: "3px solid var(--clr-accent)",
          }}
        />
      )}
      <span style={{ position: "relative", zIndex: 1, color: active ? "var(--clr-accent)" : "inherit" }}>{icon}</span>
      {!collapsed && <span style={{ position: "relative", zIndex: 1 }}>{label}</span>}
    </Link>
  );
}

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  return (
    <aside
      style={{
        width: collapsed ? 72 : 230,
        flexShrink: 0,
        background: "#ffffff",
        borderRight: "1px solid var(--clr-border)",
        minHeight: "100vh",
        padding: "20px 12px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        gap: 24,
        transition: "width 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
        position: "sticky",
        top: 0,
        zIndex: 45,
      }}
    >
      <div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 4px", marginBottom: 28 }}>
          <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background: "var(--clr-accent)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <TrendingUp size={18} color="#ffffff" strokeWidth={2.5} />
            </div>
            {!collapsed && (
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span style={{ fontWeight: 800, fontSize: 15, color: "#0f172a", letterSpacing: "-0.01em", lineHeight: 1.1 }}>
                  Smart Watchlist
                </span>
                <span style={{ fontSize: 10, fontWeight: 700, color: "var(--clr-accent)", letterSpacing: "0.05em", textTransform: "uppercase" }}>
                  Market Engine
                </span>
              </div>
            )}
          </Link>
          <button
            onClick={() => setCollapsed((v) => !v)}
            id="sidebar-toggle"
            style={{
              background: "#f8fafc",
              border: "1px solid var(--clr-border)",
              borderRadius: "50%",
              width: 24,
              height: 24,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              color: "var(--clr-text-muted)",
              transition: "all 0.15s ease",
            }}
          >
            {collapsed ? <ChevronRight size={13} /> : <ChevronLeft size={13} />}
          </button>
        </div>

        <div>
          {!collapsed && (
            <div
              style={{
                fontSize: 10,
                fontWeight: 800,
                letterSpacing: "0.08em",
                color: "var(--clr-text-faint)",
                textTransform: "uppercase",
                padding: "0 12px 10px",
              }}
            >
              Navigation
            </div>
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <NavItem href="/" icon={<LayoutGrid size={18} />} label="Overview" active={pathname === "/"} collapsed={collapsed} />
            <NavItem href="/watchlists" icon={<ListChecks size={18} />} label="Watchlists" active={pathname === "/watchlists"} collapsed={collapsed} />
            <NavItem href="/settings" icon={<Settings size={18} />} label="Settings" active={pathname === "/settings"} collapsed={collapsed} />
          </div>
        </div>
      </div>

      {/* Product-native attention status badge */}
      {!collapsed && (
        <div
          style={{
            padding: "12px 14px",
            borderRadius: "var(--radius-sm)",
            background: "rgba(16, 185, 129, 0.06)",
            border: "1px solid rgba(16, 185, 129, 0.20)",
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, fontWeight: 700, color: "var(--clr-accent)" }}>
            <span className="live-indicator-dot" />
            <span>Attention Radar Online</span>
          </div>
          <div style={{ fontSize: 11, color: "var(--clr-text-muted)", lineHeight: 1.4 }}>
            Scanning 4 signal layers: price velocity, volume, divergence, and news.
          </div>
        </div>
      )}
    </aside>
  );
}
