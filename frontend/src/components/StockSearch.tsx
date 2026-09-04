"use client";

import { useState, useCallback } from "react";
import { Search, Plus, X } from "lucide-react";
import { api } from "@/lib/api";
import type { SymbolSearchResult } from "@/lib/types";

interface Props {
  watchlistId: string;
  onAdded?: () => void;
}

export function StockSearch({ watchlistId, onAdded }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SymbolSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [adding, setAdding] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(async (q: string) => {
    if (q.length < 1) { setResults([]); return; }
    setLoading(true);
    try {
      const data = await api.searchStocks(q);
      setResults(data);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    setQuery(v);
    search(v);
  };

  const handleAdd = async (symbol: string) => {
    setAdding(symbol);
    setError(null);
    try {
      await api.addSymbol(watchlistId, symbol);
      setQuery("");
      setResults([]);
      onAdded?.();
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? `Couldn't add "${symbol}" — check the ticker is correct (e.g. AAPL, RELIANCE.NS)`
          : "Failed to add symbol"
      );
    } finally {
      setAdding(null);
    }
  };

  const trimmedQuery = query.trim().toUpperCase();
  // Not in the local catalog yet — offer to resolve it live via the
  // provider instead of dead-ending the search.
  const showAddNew =
    trimmedQuery.length > 0 &&
    !loading &&
    !results.some((r) => r.symbol === trimmedQuery);

  return (
    <div style={{ position: "relative" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ position: "relative", flex: 1 }}>
          <Search
            size={15}
            style={{
              position: "absolute",
              left: 12,
              top: "50%",
              transform: "translateY(-50%)",
              color: "var(--clr-text-muted)",
            }}
          />
          <input
            id="stock-search-input"
            type="text"
            value={query}
            onChange={handleChange}
            placeholder="Search by ticker or company…"
            style={{
              width: "100%",
              padding: "10px 12px 10px 36px",
              borderRadius: "var(--radius-sm)",
              background: "var(--clr-surface-2)",
              border: "1px solid var(--clr-border)",
              color: "var(--clr-text)",
              fontSize: 14,
              outline: "none",
              transition: "border-color 0.15s",
            }}
            onFocus={(e) => (e.target.style.borderColor = "var(--clr-accent)")}
            onBlur={(e) => (e.target.style.borderColor = "var(--clr-border)")}
          />
          {query && (
            <button
              onClick={() => { setQuery(""); setResults([]); }}
              style={{
                position: "absolute",
                right: 10,
                top: "50%",
                transform: "translateY(-50%)",
                background: "none",
                border: "none",
                cursor: "pointer",
                color: "var(--clr-text-muted)",
                display: "flex",
              }}
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Results dropdown */}
      {(results.length > 0 || showAddNew) && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 6px)",
            left: 0,
            right: 0,
            background: "var(--clr-surface)",
            border: "1px solid var(--clr-border)",
            borderRadius: "var(--radius-md)",
            boxShadow: "var(--shadow-card)",
            zIndex: 100,
            overflow: "hidden",
          }}
        >
          {results.map((r) => (
            <div
              key={r.symbol}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "10px 14px",
                borderBottom: "1px solid var(--clr-border)",
                transition: "background 0.1s",
              }}
              onMouseOver={(e) => (e.currentTarget.style.background = "var(--clr-surface-2)")}
              onMouseOut={(e) => (e.currentTarget.style.background = "")}
            >
              <div>
                <span style={{ fontWeight: 700, fontSize: 14 }}>{r.symbol}</span>
                <span style={{ color: "var(--clr-text-muted)", fontSize: 12, marginLeft: 8 }}>
                  {r.company_name}
                </span>
              </div>
              <button
                className="btn btn-primary"
                style={{ padding: "4px 12px", fontSize: 12 }}
                disabled={adding === r.symbol}
                onClick={() => handleAdd(r.symbol)}
                id={`add-${r.symbol}-btn`}
              >
                <Plus size={12} />
                {adding === r.symbol ? "Adding…" : "Add"}
              </button>
            </div>
          ))}

          {showAddNew && (
            <div style={{ padding: "10px 14px" }}>
              <div style={{ fontSize: 11, color: "var(--clr-text-faint)", marginBottom: 6 }}>
                Not in our catalog yet — add any real ticker directly:
              </div>
              <button
                className="btn btn-ghost"
                style={{ width: "100%", justifyContent: "center", fontSize: 12 }}
                disabled={adding === trimmedQuery}
                onClick={() => handleAdd(trimmedQuery)}
                id="add-new-ticker-btn"
              >
                <Plus size={12} />
                {adding === trimmedQuery ? "Looking up…" : `Add "${trimmedQuery}"`}
              </button>
            </div>
          )}
        </div>
      )}

      {error && (
        <div style={{ marginTop: 8, color: "var(--clr-critical)", fontSize: 12 }}>
          {error}
        </div>
      )}
    </div>
  );
}
