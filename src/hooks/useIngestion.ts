import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface UploadResult {
  ingestion_id: string | null;
  original_filename: string;
  normalized_filename?: string;
  report_type?: string;
  status: string;
}

export interface IngestionStatus {
  ingestion_id: string;
  db_status: string | null;
  progress: { stage?: string; current?: number; total?: number; status?: string } | null;
  error_context: Record<string, any> | null;
}

export interface FailedRow {
  row: number | string;
  id_no: string;
  field: string;
  message: string;
}

export function useUploadFiles() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (files: File[]) => {
      const form = new FormData();
      files.forEach((f) => form.append("files", f));
      const res = await api.post("/api/ingest/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
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

export function useIngestionErrors(ingestionId: string | null) {
  return useQuery({
    queryKey: ["ingestion-errors", ingestionId],
    queryFn: () =>
      api.get(`/api/ingest/${ingestionId}/errors`).then((r) => r.data as { total_failed: number; failed_rows: FailedRow[] }),
    enabled: false,
  });
}

export function useIngestionHistory() {
  return useQuery({
    queryKey: ["ingestion-history"],
    queryFn: () => api.get("/api/ingest/history?limit=50").then((r) => r.data),
    refetchInterval: 30_000,
  });
}

export function usePollingStatuses(ids: string[]) {
  const [results] = useState(() => ids.map((id) => ({ id, status: "polling" })));
  return results;
}
