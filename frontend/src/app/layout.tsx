"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./globals.css";
import { useState } from "react";
import { AuthProvider } from "@/context/AuthContext";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // Explicit, not just relying on the library default, so intent
            // reads clearly here: don't burn polling cycles on a
            // backgrounded tab (this IS the v5 default, restated on
            // purpose), and retry transient network failures with backoff
            // rather than failing a poll tick outright.
            refetchIntervalInBackground: false,
            retry: 2,
            retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10_000),
          },
        },
      })
  );

  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Smart Market Watchlist — AI Attention Engine</title>
        <meta
          name="description"
          content="AI-powered watchlist that ranks what you missed in the market and explains why it matters."
        />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>{children}</AuthProvider>
        </QueryClientProvider>
      </body>
    </html>
  );
}
