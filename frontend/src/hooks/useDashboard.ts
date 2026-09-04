// hooks/useDashboard.ts

"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { DashboardSummary, WatchlistOut } from "@/lib/types";

export function useDashboard() {
  return useQuery<DashboardSummary>({
    queryKey: ["dashboard"],
    queryFn: () => api.getDashboard(),
    refetchInterval: 20_000,
  });
}

export function useWatchlists() {
  return useQuery<WatchlistOut[]>({
    queryKey: ["watchlists"],
    queryFn: () => api.getWatchlists(),
  });
}
