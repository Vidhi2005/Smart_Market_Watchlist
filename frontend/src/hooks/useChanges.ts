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

// symbolIds omitted (or undefined) commits the whole watchlist; passing
// one or more symbol ids scopes the commit to just those symbols — see
// observation_service.commit_observations on the backend.
export function useCommitObservations(watchlistId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (symbolIds?: string[]) => api.commitObservations(watchlistId, symbolIds),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["changes", watchlistId] });
      // The header's critical-count badge reads from ["dashboard"], which
      // polls independently (every 20s) — without this it can show a
      // stale count for up to 20s after a review here.
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["watchlists"] });
    },
  });
}
