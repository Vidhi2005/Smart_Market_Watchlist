// hooks/useChanges.ts — React Query hook for /changes endpoint

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ChangesResponse } from "@/lib/types";

export function useChanges(watchlistId: string | null) {
  return useQuery<ChangesResponse>({
    queryKey: ["changes", watchlistId],
    queryFn: () => api.getChanges(watchlistId!),
    enabled: !!watchlistId,
    refetchInterval: 15_000,  // 15s auto-poll — tuned for a "live" feel
    staleTime: 8_000,
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
