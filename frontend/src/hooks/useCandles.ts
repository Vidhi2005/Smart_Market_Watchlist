"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CandleRange, CandlesResponse } from "@/lib/types";

export function useCandles(symbol: string | null, range: CandleRange) {
  return useQuery<CandlesResponse>({
    queryKey: ["candles", symbol, range],
    queryFn: () => api.getCandles(symbol!, range),
    enabled: !!symbol,
    refetchInterval: 30_000,
    staleTime: 15_000,
  });
}
