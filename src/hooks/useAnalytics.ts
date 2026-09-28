import { useMemo } from "react";
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
  /** Whitelisted record-column filters (records mode only). */
  record_filters?: Record<string, string[]>;
  /** Per date-column sub-ranges of the main range (records mode), keyed by
   * the record column key (e.g. work_date, date_range). */
  date_sub_ranges?: Record<string, { start: string; end: string }>;
  date_filter_mode?: string;
  /** Set false to disable the query (parameters still key the cache). */
  enabled?: boolean;
}

export interface ExploreResponse {
  mode: string;
  columns: { key: string; label: string; type?: string }[];
  groups?: Record<string, any>[];
  records?: Record<string, any>[];
  /** Distinct values per filterable record column (records mode). */
  filter_options?: Record<string, string[]>;
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

export interface MetricMeta {
  key: string;
  domain: "attendance" | "leave" | "training" | "employees";
  label: string;
  type: string;
  polarity?: "up_good" | "up_bad" | null;
  /** Fixed good/bad line for percentage metrics; null → relative (median). */
  pivot?: number | null;
}

export function useAnalyticsMetrics() {
  return useQuery({
    queryKey: ["analytics-metrics"],
    queryFn: () =>
      api.get("/api/analytics/metrics").then((r) => r.data as {
        domains: Record<string, string>;
        metrics: MetricMeta[];
      }),
    staleTime: 300_000,
  });
}

function filtersParam(filters?: Record<string, string[]>): string {
  return filters && Object.keys(filters).length > 0 ? JSON.stringify(filters) : "";
}

export interface TodaySnapshot {
  date: string;
  is_working_day: boolean;
  active_employees: number;
  total_swipes: number;
  swipers: number;
  late_so_far: number | null;
  on_leave: number;
  in_training: number;
  no_swipe_yet: number | null;
  last_swipe: string | null;
}

export function useAnalyticsToday(filters?: Record<string, string[]>) {
  const fp = filtersParam(filters);
  return useQuery({
    queryKey: ["analytics-today", fp],
    queryFn: () =>
      api.get(`/api/analytics/today`, { params: { filters: fp } }).then((r) => r.data as TodaySnapshot),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}

export interface Freshness {
  fact_start: string | null;
  fact_end: string | null;
  fact_rows: number;
  fact_is_empty: boolean;
  coverage: number | null;
  last_ingest: {
    filename: string; report_type: string; status: string;
    created_at: string | null; processed_at: string | null;
  } | null;
  quarantine_rows: number;
}

export function useAnalyticsFreshness(filters?: Record<string, string[]>) {
  const fp = filtersParam(filters);
  return useQuery({
    queryKey: ["analytics-freshness", fp],
    queryFn: () =>
      api.get(`/api/analytics/freshness`, { params: { filters: fp } }).then((r) => r.data as Freshness),
    staleTime: 60_000,
  });
}

export interface Signal {
  dimension: string;
  segment: string;
  domain: string;
  metric: string;
  metric_label: string;
  type: string;
  polarity?: string | null;
  current: number;
  previous: number | null;
  delta_pp: number | null;
  pct_change: number | null;
  z: number | null;
  severity: "danger" | "warning" | "info";
  direction: "up" | "down";
  good: boolean | null;
  headline: string;
  detail: string;
  drill: { dimension: string; value: string };
}

export function useAnalyticsSignals(
  dateRange: { start: string; end: string } | null,
  filters?: Record<string, string[]>
) {
  const fp = filtersParam(filters);
  return useQuery({
    queryKey: ["analytics-signals", dateRange?.start || "", dateRange?.end || "", fp],
    queryFn: () =>
      api
        .get(`/api/analytics/signals`, {
          params: { start: dateRange?.start, end: dateRange?.end, filters: fp },
        })
        .then((r) => r.data as {
          as_of: string;
          window: { start: string; end: string };
          previous_window: { start: string; end: string };
          signals: Signal[];
          health: Freshness;
        }),
    staleTime: 120_000,
  });
}

export interface ForecastWeek extends TrendPointLike {
  actual: boolean;
  bandLow?: number;
  bandHigh?: number;
}
interface TrendPointLike {
  label: string;
  value: number;
}

export interface CoverageRow {
  department: string;
  headcount: number;
  weeks: { week: string; expected_leave: number; scheduled_training: number; available: number; headcount: number }[];
}

export interface ForecastResponse {
  as_of: string;
  window_weeks: number;
  horizon_weeks: number;
  method: string;
  projection: ForecastWeek[];
  leave_forecast: ForecastWeek[];
  coverage: { weeks: string[]; departments: CoverageRow[] };
  risks: {
    id_no: string; full_name: string; department: string;
    recent_absent: number; recent_late: number;
    baseline_per_30d: number; ratio: number | null; score: number;
  }[];
}

export function useAnalyticsForecast(filters?: Record<string, string[]>) {
  const fp = filtersParam(filters);
  return useQuery({
    queryKey: ["analytics-forecast", fp],
    queryFn: () =>
      api.get(`/api/analytics/forecast`, { params: { filters: fp } }).then((r) => r.data as ForecastResponse),
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
    enabled: !!params.domain && params.enabled !== false,
  });
}

export interface MultiDomainPivotInput {
  metricsByDomain: { domain: ExploreParams["domain"]; metrics: string[] }[];
  group_by: string[];
  filters?: Record<string, string[]>;
  date_range?: { start: string; end: string } | null;
  enabled?: boolean;
}

/** Cross-subject pivot: one summary explore per subject, merged on the group key.
 * Groups present in any subject appear (missing metrics stay null → "—"). */
export function useMultiDomainPivot(input: MultiDomainPivotInput) {
  const groupKey = input.group_by.join(",");
  const results = useQueries({
    queries: input.metricsByDomain.map((d) => {
      const params: ExploreParams = {
        domain: d.domain,
        metrics: d.metrics,
        group_by: input.group_by,
        filters: input.filters,
        date_range: input.date_range,
        mode: "summary",
        page: 1,
        page_size: 2000,
      };
      return {
        queryKey: ["analytics-explore", JSON.stringify(params)],
        queryFn: () => api.post("/api/analytics/explore", params).then((r) => r.data as ExploreResponse),
        placeholderData: keepPreviousData,
        enabled: input.enabled !== false && d.metrics.length > 0,
      };
    }),
  });
  // Memoize on serialized payloads: useQueries returns a new array each render.
  const dataKey = JSON.stringify(results.map((r) => r.data?.groups ?? null));
  const rows: Record<string, any>[] = useMemo(() => {
    const merged = new Map<string, Record<string, any>>();
    const gb = groupKey ? groupKey.split(",") : [];
    const groupsByQuery = JSON.parse(dataKey) as Record<string, any>[][];
    for (const groups of groupsByQuery) {
      for (const g of groups || []) {
        const k = JSON.stringify(gb.map((c) => g[c] ?? null));
        const base = merged.get(k) || Object.fromEntries(gb.map((c) => [c, g[c] ?? "—"]));
        merged.set(k, { ...base, ...g });
      }
    }
    return [...merged.values()];
  }, [dataKey, groupKey]);
  return {
    rows,
    loading: results.some((r) => r.isLoading),
    isFetching: results.some((r) => r.isFetching),
  };
}

export interface LeaveTrendPoint {
  bucket: string;
  department: string;
  staff: number;
}

/** Staff-over-time time series: distinct staff overlapping each bucket, per department. */
export function useRangeTrend(
  domain: "leave" | "training",
  params: {
    start: string;
    end: string;
    granularity: string;
    filters?: Record<string, string[]>;
    enabled?: boolean;
  }
) {
  const key = JSON.stringify(params);
  return useQuery<{ granularity: string; start: string; end: string; rows: LeaveTrendPoint[] }>({
    queryKey: [`analytics-${domain}-trend`, key],
    queryFn: () => api.post(`/api/analytics/${domain}-trend`, params).then((r) => r.data),
    placeholderData: keepPreviousData,
    enabled: params.enabled !== false && !!params.start && !!params.end,
  });
}

/** Staff-on-leave time series (see useRangeTrend). */
export function useLeaveTrend(params: {
  start: string;
  end: string;
  granularity: string;
  filters?: Record<string, string[]>;
  enabled?: boolean;
}) {
  return useRangeTrend("leave", params);
}

/** Staff-in-training time series (see useRangeTrend). */
export function useTrainingTrend(params: {
  start: string;
  end: string;
  granularity: string;
  filters?: Record<string, string[]>;
  enabled?: boolean;
}) {
  return useRangeTrend("training", params);
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
