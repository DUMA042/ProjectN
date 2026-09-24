import { useQuery, useQueries, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function toApiFilters(filters: Record<string, Set<string>>): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const [k, s] of Object.entries(filters)) {
    if (s.size > 0) out[k] = [...s];
  }
  return out;
}

export interface ExploreParams {
  domain: "attendance" | "leave" | "training" | "employees";
  metrics?: string[];
  group_by?: string[];
  filters?: Record<string, string[]>;
  date_range?: { start: string; end: string } | null;
  compare?: "previous" | null;
  mode?: "summary" | "records";
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
  search?: string;
}

export interface ExploreResponse {
  mode: string;
  columns: { key: string; label: string; type?: string }[];
  groups?: Record<string, any>[];
  records?: Record<string, any>[];
  total: number;
  page: number;
  page_size: number;
  totals?: Record<string, any>;
  previous_totals?: Record<string, any>;
  previous_range?: { start: string; end: string };
}

export function useAnalyticsDimensions() {
  return useQuery({
    queryKey: ["analytics-dimensions"],
    queryFn: () =>
      api.get("/api/analytics/dimensions").then((r) => r.data as {
        dimensions: { key: string; label: string; kind: string }[];
        options: Record<string, string[]>;
      }),
    staleTime: 300_000,
  });
}

export function useAnalyticsOverview() {
  return useQuery({
    queryKey: ["analytics-overview"],
    queryFn: () => api.get("/api/analytics/overview").then((r) => r.data),
    staleTime: 60_000,
  });
}

export function useAnalyticsExplore(params: ExploreParams) {
  const key = JSON.stringify(params);
  return useQuery<ExploreResponse>({
    queryKey: ["analytics-explore", key],
    queryFn: () => api.post("/api/analytics/explore", params).then((r) => r.data),
    placeholderData: keepPreviousData,
    enabled: !!params.domain,
  });
}

export function useAnalyticsRefresh() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post("/api/analytics/refresh").then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["analytics-explore"] }),
  });
}

export interface ScopedTotalsInput {
  domain: ExploreParams["domain"];
  metrics: string[];
}

/** Scope-aware totals for several domains (used by the Overview KPI strip). */
export function useScopedTotals(
  domains: ScopedTotalsInput[],
  filters: Record<string, string[]>,
  dateRange: { start: string; end: string } | null,
  compare: boolean
) {
  return useQueries({
    queries: domains.map((d) => {
      const params: ExploreParams = {
        domain: d.domain,
        metrics: d.metrics,
        group_by: [],
        filters,
        date_range: dateRange,
        compare: compare ? "previous" : null,
        mode: "summary",
        page: 1,
        page_size: 1,
      };
      return {
        queryKey: ["analytics-explore", JSON.stringify(params)],
        queryFn: () => api.post("/api/analytics/explore", params).then((r) => r.data as ExploreResponse),
        placeholderData: keepPreviousData,
      };
    }),
  });
}
