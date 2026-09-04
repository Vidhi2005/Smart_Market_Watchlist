"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutGrid, ListChecks, Settings, ChevronLeft, ChevronRight, TrendingUp } from "lucide-react";

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
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "10px 12px",
        borderRadius: "var(--radius-sm)",
        fontSize: 14,
        fontWeight: active ? 700 : 500,
        color: active ? "var(--clr-text)" : "var(--clr-text-muted)",
        background: active ? "var(--clr-surface-2)" : "transparent",
        borderLeft: active ? "2px solid var(--clr-accent)" : "2px solid transparent",
        textDecoration: "none",
      }}
    >
      {icon}
      {!collapsed && <span>{label}</span>}
    </Link>
  );
}

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  return (
    <aside
      style={{
        width: collapsed ? 72 : 224,
        flexShrink: 0,
        borderRight: "1px solid var(--clr-border)",
        minHeight: "100vh",
        padding: "20px 12px",
        display: "flex",
        flexDirection: "column",
        gap: 24,
        transition: "width 0.2s ease",
        position: "sticky",
        top: 0,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 4px" }}>
        <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
          <div
            style={{
              width: 30,
              height: 30,
              borderRadius: 8,
              background: "var(--clr-accent)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <TrendingUp size={16} color="#fff" />
          </div>
          {!collapsed && <span style={{ fontWeight: 800, fontSize: 15, color: "var(--clr-text)" }}>Watchlist</span>}
        </Link>
        <button
          onClick={() => setCollapsed((v) => !v)}
          id="sidebar-toggle"
          style={{
            background: "none",
            border: "1px solid var(--clr-border)",
            borderRadius: "50%",
            width: 22,
            height: 22,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            color: "var(--clr-text-muted)",
          }}
        >
          {collapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
        </button>
      </div>

      <div>
        {!collapsed && (
          <div
            style={{
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: "0.08em",
              color: "var(--clr-text-faint)",
              textTransform: "uppercase",
              padding: "0 12px 8px",
            }}
          >
            Navigation
          </div>
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <NavItem href="/" icon={<LayoutGrid size={17} />} label="Overview" active={pathname === "/"} collapsed={collapsed} />
          <NavItem href="/watchlists" icon={<ListChecks size={17} />} label="Watchlists" active={pathname === "/watchlists"} collapsed={collapsed} />
          <NavItem href="/settings" icon={<Settings size={17} />} label="Settings" active={pathname === "/settings"} collapsed={collapsed} />
        </div>
      </div>
    </aside>
  );
}
