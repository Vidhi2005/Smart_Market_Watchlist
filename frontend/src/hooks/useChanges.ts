// hooks/useChanges.ts — React Query hook for /changes endpoint

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ChangesResponse } from "@/lib/types";

/**
 * Adaptive polling: 15s while a market this watchlist could care about is
 * open (matches the "live" feel the product wants), backed off to 2min
 * when both US and India are closed — no new snapshot is going to appear
 * outside trading hours, so polling at the normal cadence would just be
 * wasted requests. `refetchIntervalInBackground: false` is a QueryClient
 * default (see layout.tsx) so a backgrounded tab doesn't poll at all.
 */
export function useChanges(watchlistId: string | null, marketOpen: boolean = true) {
  return useQuery<ChangesResponse>({
    queryKey: ["changes", watchlistId],
    queryFn: () => api.getChanges(watchlistId!),
    enabled: !!watchlistId,
    refetchInterval: marketOpen ? 15_000 : 120_000,
    staleTime: marketOpen ? 8_000 : 60_000,
  });
}

export function useCommitObservations(watchlistId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.commitObservations(watchlistId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["changes", watchlistId] });
    },
  });
}
