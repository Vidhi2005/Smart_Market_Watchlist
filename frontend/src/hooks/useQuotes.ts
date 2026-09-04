"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { QuoteOut } from "@/lib/types";

export function useQuotes(watchlistId: string | null) {
  return useQuery<QuoteOut[]>({
    queryKey: ["quotes", watchlistId],
    queryFn: () => api.getQuotes(watchlistId!),
    enabled: !!watchlistId,
    refetchInterval: 15_000,
    staleTime: 8_000,
  });
}
