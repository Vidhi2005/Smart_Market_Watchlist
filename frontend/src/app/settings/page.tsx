"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2, Check, Globe2, PlayCircle } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { SystemStatusBadge } from "@/components/SystemStatusBadge";
import { MarketStatusPill } from "@/components/MarketStatusPill";
import { useAuth } from "@/context/AuthContext";
import { useDashboard, useWatchlists } from "@/hooks/useDashboard";
import { COUNTRIES } from "@/lib/countries";
import { api } from "@/lib/api";

function SettingsContent() {
  const qc = useQueryClient();
  const { user, logout, updateProfile } = useAuth();
  const { data: dashboard } = useDashboard();
  const { data: watchlists } = useWatchlists();
  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [demoRunning, setDemoRunning] = useState(false);
  const [demoResult, setDemoResult] = useState<string | null>(null);
  const currentCountry = COUNTRIES.find((c) => c.label === user?.country);
  const [countryCode, setCountryCode] = useState(currentCountry?.code ?? "IN");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dirty =
    (displayName.trim() !== "" && displayName.trim() !== user?.display_name) ||
    countryCode !== (currentCountry?.code ?? "IN");

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const country = COUNTRIES.find((c) => c.code === countryCode);
      await updateProfile({
        display_name: displayName.trim(),
        country: country?.label,
        timezone: country?.timezone,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleRunDemo = async () => {
    const watchlistId = watchlists?.[0]?.id;
    if (!watchlistId) return;
    setDemoRunning(true);
    setDemoResult(null);
    try {
      const res = await api.runDemoScenario(watchlistId);
      setDemoResult(`Seeded ${res.symbols.length} symbols as if you'd been away ${res.away_for_minutes} minutes.`);
      qc.invalidateQueries({ queryKey: ["changes"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["quotes"] });
      qc.invalidateQueries({ queryKey: ["watchlists"] });
    } catch (err) {
      setDemoResult(err instanceof Error ? err.message : "Demo scenario failed");
    } finally {
      setDemoRunning(false);
    }
  };

  return (
    <>
      <h1 style={{ fontSize: 22, fontWeight: 800, marginBottom: 4 }}>Settings</h1>
      <p style={{ fontSize: 13, color: "var(--clr-text-muted)", marginBottom: 24 }}>
        Manage your profile and see system status.
      </p>

      <div className="settings-grid">
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {/* Profile */}
        <div className="card">
          <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>Profile</h2>

          <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13, fontWeight: 600, marginBottom: 14 }}>
            Display name
            <input
              id="settings-display-name"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              style={{
                padding: "10px 12px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--clr-border)",
                background: "var(--clr-surface-2)",
                fontSize: 14,
                fontFamily: "inherit",
                color: "var(--clr-text)",
                outline: "none",
              }}
            />
          </label>

          <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13, fontWeight: 600, marginBottom: 14 }}>
            Country
            <div style={{ position: "relative" }}>
              <Globe2
                size={14}
                style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--clr-text-muted)", pointerEvents: "none" }}
              />
              <select
                id="settings-country"
                value={countryCode}
                onChange={(e) => setCountryCode(e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px 12px 10px 34px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--clr-border)",
                  background: "var(--clr-surface-2)",
                  fontSize: 14,
                  fontFamily: "inherit",
                  color: "var(--clr-text)",
                  outline: "none",
                  appearance: "none",
                }}
              >
                {COUNTRIES.map((c) => (
                  <option key={c.code} value={c.code}>{c.label}</option>
                ))}
              </select>
            </div>
            <span style={{ fontSize: 11, fontWeight: 400, color: "var(--clr-text-faint)" }}>
              Currently: {user?.timezone ?? "UTC"} — drives your dashboard greeting.
            </span>
          </label>

          <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13, fontWeight: 600, marginBottom: 14 }}>
            Email
            <input
              type="email"
              value={user?.email ?? ""}
              disabled
              style={{
                padding: "10px 12px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--clr-border)",
                background: "var(--clr-bg-alt)",
                fontSize: 14,
                fontFamily: "inherit",
                color: "var(--clr-text-muted)",
                outline: "none",
              }}
            />
          </label>

          {error && <div style={{ fontSize: 12, color: "var(--clr-critical)", marginBottom: 10 }}>{error}</div>}

          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={!dirty || saving}
            id="settings-save-btn"
          >
            {saving ? <Loader2 size={14} className="spin" /> : saved ? <Check size={14} /> : null}
            {saving ? "Saving…" : saved ? "Saved" : "Save changes"}
          </button>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {/* Account */}
        <div className="card">
          <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Account</h2>
          <div style={{ fontSize: 13, color: "var(--clr-text-muted)", marginBottom: 16 }}>
            Member since {user ? new Date(user.created_at).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" }) : "—"}
          </div>
          <button className="btn btn-ghost" onClick={logout} id="settings-logout-btn">
            Log out
          </button>
        </div>

        {/* System */}
        <div className="card">
          <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>System status</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <SystemStatusBadge />
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <MarketStatusPill label="US Market" isOpen={dashboard?.us_market_open ?? false} />
              <MarketStatusPill label="India Market" isOpen={dashboard?.indian_market_open ?? false} />
            </div>
            {dashboard?.last_poll_at && (
              <div style={{ fontSize: 12, color: "var(--clr-text-muted)" }}>
                Last market data poll: {new Date(dashboard.last_poll_at).toLocaleString()}
              </div>
            )}
          </div>
        </div>

        {/* Demo Mode */}
        <div className="card">
          <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 6 }}>Demo Mode</h2>
          <p style={{ fontSize: 12, color: "var(--clr-text-muted)", marginBottom: 14, lineHeight: 1.5 }}>
            Seeds a deterministic &quot;you were away for 4h12m&quot; scenario (NVDA +7.8%, TSLA -3.1%,
            MSFT +2.4%, plus two quiet stocks for contrast) through the real ingestion → scoring →
            event pipeline — no external API calls, same result every time.
          </p>
          <button
            className="btn btn-primary"
            onClick={handleRunDemo}
            disabled={demoRunning || !watchlists?.[0]?.id}
            id="run-demo-btn"
          >
            {demoRunning ? <Loader2 size={14} className="spin" /> : <PlayCircle size={14} />}
            {demoRunning ? "Seeding…" : "Run demo scenario"}
          </button>
          {demoResult && (
            <div style={{ fontSize: 12, color: "var(--clr-text-muted)", marginTop: 10 }}>
              {demoResult} Head to Overview to see it.
            </div>
          )}
        </div>
      </div>
      </div>
    </>
  );
}

export default function SettingsPage() {
  return (
    <AppShell>
      <SettingsContent />
    </AppShell>
  );
}
