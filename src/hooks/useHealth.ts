import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface HealthState {
  db: string;
  status?: string;
}

/** Single source of truth for "is the local service reachable?".
 *  Shared by StatusBar and the offline banner so only one poller exists. */
export function useHealth() {
  return useQuery<HealthState>({
    queryKey: ["health"],
    queryFn: () => api.get("/api/health").then((r) => r.data),
    refetchInterval: 30_000,
    retry: 0,
    staleTime: 10_000,
  });
}

export function isHealthy(state?: HealthState): boolean {
  return state?.db === "connected";
}
