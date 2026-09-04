"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { TrendingUp, Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

export default function LoginPage() {
  const { user, isLoading, login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!isLoading && user) router.replace("/");
  }, [isLoading, user, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
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

        <h1 style={{ fontSize: 20, fontWeight: 800, marginBottom: 4 }}>Welcome back</h1>
        <p style={{ fontSize: 13, color: "var(--clr-text-muted)", marginBottom: 20 }}>
          Log in to see what changed while you were away.
        </p>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <Field label="Email" type="email" value={email} onChange={setEmail} id="login-email" autoComplete="email" />
          <Field label="Password" type="password" value={password} onChange={setPassword} id="login-password" autoComplete="current-password" />

          {error && <div style={{ fontSize: 12, color: "var(--clr-critical)" }}>{error}</div>}

          <button type="submit" className="btn btn-primary" disabled={submitting} style={{ justifyContent: "center", marginTop: 4 }} id="login-submit">
            {submitting ? <Loader2 size={14} className="spin" /> : "Log in"}
          </button>
        </form>

        <div style={{ fontSize: 13, color: "var(--clr-text-muted)", marginTop: 18, textAlign: "center" }}>
          Don&apos;t have an account?{" "}
          <Link href="/signup" style={{ color: "var(--clr-accent)", fontWeight: 600, textDecoration: "none" }}>
            Sign up
          </Link>
        </div>

        <div style={{ fontSize: 11, color: "var(--clr-text-faint)", marginTop: 14, textAlign: "center" }}>
          Demo account: demo@smartwatchlist.dev / demo12345
        </div>
      </motion.div>
    </div>
  );
}

function Field({
  label, type, value, onChange, id, autoComplete,
}: {
  label: string; type: string; value: string; onChange: (v: string) => void; id: string; autoComplete: string;
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
    </label>
  );
}
