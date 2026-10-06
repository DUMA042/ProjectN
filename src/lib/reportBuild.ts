import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export type HashMode = "names_only" | "names_and_ids";
export type BuildFileState = "pending" | "active" | "done" | "error";

export interface BuildJobFile {
  id: string;
  state: BuildFileState;
  error: string | null;
}

export interface BuildStartResult {
  job_id: string;
  needs_hashing: boolean;
  individual_files: { id: string; display_name: string; row_count: number }[];
  files: { id: string; display_name: string; classification?: string }[];
  hash_warning_names_and_ids: string;
}

export interface BuildJob {
  id: string;
  file_ids: string[];
  stage: string;
  stage_detail: string;
  files: BuildJobFile[];
  hash_mode: HashMode | null;
  created_at: string;
  updated_at: string;
  payload: Record<string, unknown>;
}

/** Stage order for progress display (mirrors owl.reports.jobs.STAGES). */
export const BUILD_STAGES = [
  "added",
  "inspected",
  "hashing",
  "validated",
  "sent_to_ai",
  "analysis",
  "topics_ready",
  "generating",
  "complete",
] as const;

const STAGE_LABELS: Record<string, string> = {
  added: "Files added",
  inspected: "Files inspected",
  hashing: "Hashing individual files",
  validated: "Files validated",
  sent_to_ai: "Sending files to AI",
  analysis: "AI analysis",
  topics_ready: "Topics ready",
  generating: "Generating report",
  complete: "Report complete",
  cancelled: "Cancelled",
  resolving: "Finding employees",
  querying: "Computing attendance",
  rendering: "Writing document",
};

export function buildStageLabel(stage: string): string {
  return STAGE_LABELS[stage] || stage;
}

/** Inspect build files; reports whether hashing is needed. */
export async function startBuild(fileIds: string[]): Promise<BuildStartResult> {
  const res = await api.post("/api/reports/build/start", { file_ids: fileIds });
  return res.data as BuildStartResult;
}

/** Hash individual files (mode chosen by the user); advances to validated. */
export async function hashBuild(
  jobId: string,
  mode: HashMode
): Promise<{ job_id: string; stage: string; hashed_ids: string[] }> {
  const res = await api.post(`/api/reports/build/${jobId}/hash`, { mode });
  return res.data;
}

export async function fetchBuildJob(jobId: string): Promise<BuildJob> {
  const res = await api.get(`/api/reports/build/jobs/${jobId}`);
  return res.data as BuildJob;
}

export interface DetectedTopic {
  name: string;
  coverage: string;
  suggested_focus: "low" | "medium" | "high";
}

export interface RecommendedRange {
  min_words: number;
  max_words: number;
  reasoning: string;
}

export interface TopicChoice {
  name: string;
  include: boolean;
  focus: "low" | "medium" | "high";
}

/** Ask the AI to review the files; returns detected topics + range advice. */
export async function analyzeBuild(
  jobId: string
): Promise<{ job_id: string; stage: string; topics: DetectedTopic[]; recommended_range: RecommendedRange }> {
  // Analysis can approach the provider timeout: override the shared 15s client cap.
  const res = await api.post(`/api/reports/build/${jobId}/analyze`, undefined, { timeout: 120_000 });
  return res.data;
}

/** Store topic/focus/word-range choices for generation. */
export async function configureBuild(
  jobId: string,
  topics: TopicChoice[],
  wordRange: { min_words: number; max_words: number }
): Promise<{ job_id: string; stage: string }> {
  const res = await api.post(`/api/reports/build/${jobId}/configure`, {
    topics,
    word_range: wordRange,
  });
  return res.data;
}

export interface ReportChart {
  title: string;
  name: string;
  url: string;
}

export interface ReportView {
  job_id: string;
  markdown: string;
  charts: ReportChart[];
  download_url: string;
}

/** Generate all sections, charts, and the Word document (long; poll meanwhile). */
export async function generateBuild(
  jobId: string
): Promise<{ job_id: string; stage: string; charts: { title: string; name: string }[] }> {
  // Multi-topic generation takes minutes: override the shared 15s client cap.
  const res = await api.post(`/api/reports/build/${jobId}/generate`, undefined, { timeout: 600_000 });
  return res.data;
}

/** Preview payload for a completed report. */
export async function fetchReportView(jobId: string): Promise<ReportView> {
  const res = await api.get(`/api/reports/build/${jobId}/report`);
  return res.data as ReportView;
}

export interface StoredReport {
  entry_id: string;
  job_id: string;
  filename: string;
  created_at: string;
  topics: string[];
  word_range?: { min_words: number; max_words: number } | null;
  download_url: string;
}

/** All stored reports (filesystem-backed: survives reloads). */
export function useStoredReports() {
  return useQuery<{ reports: StoredReport[] }>({
    queryKey: ["report-builds"],
    queryFn: () => api.get("/api/reports/builds").then((r) => r.data),
    staleTime: 30_000,
  });
}

/** Delete a stored report. Refetches the library. */
export function useDeleteStoredReport() {
  const qc = useQueryClient();
  return async (entryId: string) => {
    await api.delete(`/api/reports/builds/${entryId}`);
    await qc.invalidateQueries({ queryKey: ["report-builds"] });
  };
}

/** Cancel a running build; server cleans up created files. */
export async function cancelBuild(jobId: string): Promise<{ cancelled: boolean; removed_hashed: number }> {
  const res = await api.post(`/api/reports/build/${jobId}/cancel`);
  return res.data;
}

/** Poll the job while `active` (hashing/validating/generating). */
export function useBuildJob(jobId: string | null, active: boolean) {
  return useQuery<BuildJob>({
    queryKey: ["report-build-job", jobId],
    queryFn: () => fetchBuildJob(jobId as string),
    enabled: !!jobId,
    refetchInterval: active ? 1500 : false,
  });
}
