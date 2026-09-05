"use client";

import { Bell, RefreshCw } from "lucide-react";
import type { DashboardSummary } from "@/lib/types";
import { MarketStatusPill } from "./MarketStatusPill";
import { SystemStatusBadge } from "./SystemStatusBadge";
import { UserMenu } from "./UserMenu";

interface HeaderProps {
  summary?: DashboardSummary;
  onTriggerPoll?: () => void;
  polling?: boolean;
}

export function Header({ summary, onTriggerPoll, polling }: HeaderProps) {
  return (
    <header
      style={{
        background: "rgba(255, 255, 255, 0.92)",
        backdropFilter: "blur(8px)",
        WebkitBackdropFilter: "blur(8px)",
        borderBottom: "1px solid var(--clr-border)",
        position: "sticky",
        top: 0,
        zIndex: 35,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          height: 62,
          padding: "0 24px",
        }}
      >
        {/* System status */}
        <SystemStatusBadge />

        {/* Status bar */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {summary && (
            <>
              <MarketStatusPill label="US Market" isOpen={summary.us_market_open} />
              <MarketStatusPill label="India Market" isOpen={summary.indian_market_open} />

              {summary.critical_count > 0 && (
                <div className="badge badge-critical">
                  <Bell size={11} />
                  {summary.critical_count} critical
                </div>
              )}
            </>
          )}

          <button
            className="btn btn-ghost"
            onClick={onTriggerPoll}
            disabled={polling}
            style={{ fontSize: 13 }}
            id="trigger-poll-btn"
          >
            <RefreshCw size={14} className={polling ? "spin" : ""} />
            {polling ? "Polling…" : "Refresh"}
          </button>

          <UserMenu />
        </div>
      </div>
    </header>
  );
}
