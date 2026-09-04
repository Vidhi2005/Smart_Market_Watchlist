"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => api.getHealth(),
    refetchInterval: 30_000,
    retry: 1,
  });
}
