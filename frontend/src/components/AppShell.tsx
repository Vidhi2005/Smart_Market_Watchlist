"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { MotionConfig } from "framer-motion";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { RequireAuth } from "./RequireAuth";
import { useDashboard } from "@/hooks/useDashboard";
import { api } from "@/lib/api";

function ShellInner({ children }: { children: React.ReactNode }) {
  const qc = useQueryClient();
  const { data: dashboard } = useDashboard();
  const [polling, setPolling] = useState(false);

  const handleTriggerPoll = async () => {
    setPolling(true);
    try {
      await api.triggerPoll();
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ["changes"] });
        qc.invalidateQueries({ queryKey: ["dashboard"] });
        qc.invalidateQueries({ queryKey: ["quotes"] });
        setPolling(false);
      }, 3000);
    } catch {
      setPolling(false);
    }
  };

  return (
    // reducedMotion="user" makes every framer-motion animation in the
    // authenticated app (here and in every child component) automatically
    // respect the OS-level prefers-reduced-motion setting, without each
    // component needing its own media-query check.
    <MotionConfig reducedMotion="user">
      <div className="ambient-bg">
        <div className="ambient-texture" />
      </div>
      <div className="app-content-layer" style={{ display: "flex" }}>
        <Sidebar />
        <div style={{ flex: 1, minWidth: 0 }}>
          <Header summary={dashboard} onTriggerPoll={handleTriggerPoll} polling={polling} />
          <main className="container" style={{ paddingBlock: 32 }}>
            {children}
          </main>
        </div>
      </div>
    </MotionConfig>
  );
}

/** Sidebar + top bar + auth guard, shared by every authenticated page. */
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth>
      <ShellInner>{children}</ShellInner>
    </RequireAuth>
  );
}
