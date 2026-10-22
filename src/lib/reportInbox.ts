import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { buildCSVText, buildExportFileName } from "@/lib/csvExport";
import { saveBlob } from "@/lib/download";

export interface InboxFile {
  id: string;
  display_name: string;
  stored_name: string;
  source: string;
  row_count: number;
  byte_size: number;
  sent_at: string;
  /** "inbox" (new arrival) or "build" (queued for building); legacy entries lack it. */
  status?: "inbox" | "build";
  moved_at?: string | null;
  /** "individual" (has an Employee-ID column) or "non_individual". */
  classification?: "individual" | "non_individual";
}

/** Unprocessed count: files not yet moved to the Build section. */
export function unprocessedCount(files: InboxFile[]): number {
  return files.filter((f) => (f.status || "inbox") !== "build").length;
}

/** Move a file between Inbox and Build. Refetches the manifest. */
export function useMoveInboxFile() {
  const qc = useQueryClient();
  return async (id: string, status: "inbox" | "build") => {
    const res = await api.post(`/api/reports/inbox/${id}/move`, { status });
    await qc.invalidateQueries({ queryKey: ["report-inbox"] });
    return res.data as InboxFile;
  };
}

export type DateRangeLike = { startDate?: string; endDate?: string };

/** Serialize rows exactly like a CSV download and store them in the Report Builder inbox. */
export async function sendToReportBuilder(
  rows: Record<string, unknown>[],
  chartName: string,
  source: string,
  dateRange?: DateRangeLike
): Promise<InboxFile> {
  const csv_text = buildCSVText(rows as Record<string, any>[]);
  if (!csv_text) throw new Error("No rows to send");
  const filename = buildExportFileName(chartName, dateRange);
  const res = await api.post("/api/reports/inbox", {
    filename,
    source: source || chartName,
    csv_text,
  });
  return res.data as InboxFile;
}

/** Manifest of sent files (newest first), for the Report Builder page. */
export function useReportInbox() {
  return useQuery<{ files: InboxFile[] }>({
    queryKey: ["report-inbox"],
    queryFn: () => api.get("/api/reports/inbox").then((r) => r.data),
    staleTime: 30_000,
  });
}

/** Download a stored inbox file back to the browser. */
export async function downloadInboxFile(file: InboxFile): Promise<void> {
  const res = await api.get(`/api/reports/inbox/${file.id}/download`, {
    responseType: "blob",
  });
  saveBlob(
    new Blob([res.data], { type: "text/csv;charset=utf-8;" }),
    file.display_name
  );
}

/** Permanently delete a stored inbox file. Refetches the manifest. */
export function useDeleteInboxFile() {
  const qc = useQueryClient();
  return async (id: string) => {
    await api.delete(`/api/reports/inbox/${id}`);
    await qc.invalidateQueries({ queryKey: ["report-inbox"] });
  };
}
