"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { QuoteOut } from "@/lib/types";

// Same adaptive-polling reasoning as useChanges: no new snapshot arrives
// outside trading hours, so back off when both markets are closed.
export function useQuotes(watchlistId: string | null, marketOpen: boolean = true) {
  return useQuery<QuoteOut[]>({
    queryKey: ["quotes", watchlistId],
    queryFn: () => api.getQuotes(watchlistId!),
    enabled: !!watchlistId,
    refetchInterval: marketOpen ? 15_000 : 120_000,
    staleTime: marketOpen ? 8_000 : 60_000,
  });
}
