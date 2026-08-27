import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface UploadResult {
  ingestion_id: string | null;
  original_filename: string;
  normalized_filename?: string;
  report_type?: string;
  status: string;
  quarantine_reason?: string | null;
  error?: string;
}

export interface StageInfo {
  label: string;
  percent: number | null;
  current: number | null;
  total: number | null;
}

export interface IngestionStatus {
  ingestion_id: string;
  db_status: string | null;
  filename: string | null;
  report_type: string | null;
  stage_info: StageInfo;
  error_context: Record<string, any> | null;
}

export interface FailedRow {
  row: number | string;
  id_no: string;
  field: string;
  message: string;
}

export interface FailureBreakdownItem {
  reason: string;
  count: number;
}

export interface TableBreakdown {
  table: string;
  rows_added: number;
  rows_failed: number;
}

export interface IngestionDetails {
  ingestion_id: string;
  filename: string;
  original_filename: string;
  report_type: string | null;
  status: string;
  created_at: string | null;
  processed_at: string | null;
  duration_seconds: number | null;
  summary: {
    rows_loaded: number;
    rows_failed: number;
    validation_rejected: number;
  };
  tables_breakdown: TableBreakdown[];
  processor_report: {
    rows_read?: number | null;
    successes?: number | null;
    partial_successes?: number | null;
    failures?: number | null;
    updates?: number | null;
    new_inserts?: number | null;
    warning_count?: number | null;
    failure_count?: number | null;
  } | null;
  failed_rows_total: number;
  failure_breakdown: FailureBreakdownItem[];
  failed_rows: FailedRow[];
}

// ── Quarantine ───────────────────────────────────────────────────────────────

export type QuarantineType = "swipes" | "trainings";

export interface QuarantineRow {
  id: number;
  row_key: string;
  employee_name: string | null;
  location: string | null;
  venue: string | null;
  consultant: string | null;
  title: string | null;
  start_date: string | null;
  end_date: string | null;
  event_time: string | null;
  quarantined_at: string | null;
}

export interface QuarantineListResponse {
  type: QuarantineType;
  total: number;
  page: number;
  size: number;
  distinct_names: number;
  rows: QuarantineRow[];
}

export function useQuarantineList(params: {
  type: QuarantineType;
  search: string;
  startDate: string;
  endDate: string;
  page: number;
  size: number;
}) {
  return useQuery({
    queryKey: ["quarantine", params.type, params.search, params.startDate, params.endDate, params.page, params.size],
    queryFn: () =>
      api
        .get("/api/quarantine", {
          params: {
            type: params.type,
            search: params.search || undefined,
            start_date: params.startDate || undefined,
            end_date: params.endDate || undefined,
            page: params.page,
            size: params.size,
          },
        })
        .then((r) => r.data as QuarantineListResponse),
    staleTime: 30_000,
  });
}

export function useDeleteQuarantine() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ type, ids }: { type: QuarantineType; ids: number[] }) =>
      api
        .delete(`/api/quarantine/${type}`, { data: { ids } })
        .then((r) => r.data as { status: string; deleted: number }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["quarantine"] }),
  });
}

export function useReprocessQuarantine() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ type, ids }: { type: QuarantineType; ids: number[] }) =>
      api
        .post(`/api/quarantine/reprocess?type=${type}`, { ids })
        .then(
          (r) =>
            r.data as {
              status: string;
              succeeded: number;
              failed_count: number;
              failures: { id: number; error: string }[];
              results: { id: number; ok: boolean; error?: string }[];
            }
        ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["quarantine"] }),
  });
}

// ── Ingestion ────────────────────────────────────────────────────────────────

export function useUploadFiles() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (files: File[]) => {
      const form = new FormData();
      files.forEach((f) => form.append("files", f));
      const res = await api.post("/api/ingest/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 180_000,
      });
      return res.data as { results: UploadResult[]; rejected: { filename: string; reason: string }[] };
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ingestion-history"] }),
  });
}

export function useIngestionStatus(ingestionId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ["ingestion-status", ingestionId],
    queryFn: () => api.get(`/api/ingest/status/${ingestionId}`).then((r) => r.data as IngestionStatus),
    enabled: enabled && !!ingestionId,
    refetchInterval: 2000,
    staleTime: 1000,
  });
}

export function useIngestionDetails(ingestionId: string | null) {
  return useQuery({
    queryKey: ["ingestion-details", ingestionId],
    queryFn: () => api.get(`/api/ingest/${ingestionId}/details`).then((r) => r.data as IngestionDetails),
    enabled: !!ingestionId,
    staleTime: 30_000,
  });
}

export function useForgetIngestion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ingestionId: string) =>
      api
        .post(`/api/ingest/${ingestionId}/forget`)
        .then((r) => r.data as { status: string; filename: string; message: string }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ingestion-history"] }),
  });
}

export function useIngestionHistory() {
  return useQuery({
    queryKey: ["ingestion-history"],
    queryFn: () => api.get("/api/ingest/history?limit=50").then((r) => r.data),
    refetchInterval: 30_000,
  });
}
