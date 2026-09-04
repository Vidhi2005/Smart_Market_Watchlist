"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { TrendingUp, Loader2, Globe2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { COUNTRIES, detectTimezone, guessCountryCode } from "@/lib/countries";

export default function SignupPage() {
  const { user, isLoading, signup } = useAuth();
  const router = useRouter();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [countryCode, setCountryCode] = useState(() => guessCountryCode() ?? "IN");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!isLoading && user) router.replace("/");
  }, [isLoading, user, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setSubmitting(true);
    try {
      const country = COUNTRIES.find((c) => c.code === countryCode);
      // Prefer the browser's own detected timezone when it matches the
      // selected country (more precise than the country's single
      // representative zone — e.g. catches US sub-timezones correctly);
      // otherwise fall back to the country's representative timezone.
      const detected = detectTimezone();
      const timezone = country && guessCountryCode() === countryCode ? detected : country?.timezone ?? "UTC";
      await signup(email, password, displayName, country?.label ?? "", timezone);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-bg">
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="card auth-card"
        style={{ width: "100%", maxWidth: 380 }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 24 }}>
          <div
            style={{
              width: 34,
              height: 34,
              borderRadius: 10,
              background: "var(--clr-accent)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <TrendingUp size={18} color="#fff" />
          </div>
          <div style={{ fontWeight: 800, fontSize: 17 }}>Smart Watchlist</div>
        </div>

        <h1 style={{ fontSize: 20, fontWeight: 800, marginBottom: 4 }}>Create your account</h1>
        <p style={{ fontSize: 13, color: "var(--clr-text-muted)", marginBottom: 20 }}>
          Get a personal watchlist with your own US and Indian market signals.
        </p>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <Field label="Name" type="text" value={displayName} onChange={setDisplayName} id="signup-name" autoComplete="name" />
          <Field label="Email" type="email" value={email} onChange={setEmail} id="signup-email" autoComplete="email" />
          <Field label="Password" type="password" value={password} onChange={setPassword} id="signup-password" autoComplete="new-password" hint="At least 8 characters" />

          <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13, fontWeight: 600 }}>
            Country
            <div style={{ position: "relative" }}>
              <Globe2
                size={14}
                style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--clr-text-muted)", pointerEvents: "none" }}
              />
              <select
                id="signup-country"
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
              Used to show times (like your dashboard greeting) in your local timezone.
            </span>
          </label>

          {error && <div style={{ fontSize: 12, color: "var(--clr-critical)" }}>{error}</div>}

          <button type="submit" className="btn btn-primary" disabled={submitting} style={{ justifyContent: "center", marginTop: 4 }} id="signup-submit">
            {submitting ? <Loader2 size={14} className="spin" /> : "Create account"}
          </button>
        </form>

        <div style={{ fontSize: 13, color: "var(--clr-text-muted)", marginTop: 18, textAlign: "center" }}>
          Already have an account?{" "}
          <Link href="/login" style={{ color: "var(--clr-accent)", fontWeight: 600, textDecoration: "none" }}>
            Log in
          </Link>
        </div>
      </motion.div>
    </div>
  );
}

function Field({
  label, type, value, onChange, id, autoComplete, hint,
}: {
  label: string; type: string; value: string; onChange: (v: string) => void; id: string; autoComplete: string; hint?: string;
}) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13, fontWeight: 600 }}>
      {label}
      <input
        id={id}
        type={type}
        value={value}
        autoComplete={autoComplete}
        required
        onChange={(e) => onChange(e.target.value)}
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
      {hint && <span style={{ fontSize: 11, fontWeight: 400, color: "var(--clr-text-faint)" }}>{hint}</span>}
    </label>
  );
}
