import { useState, useCallback, useRef } from "react";
import { motion } from "framer-motion";
import { Upload, RotateCcw } from "lucide-react";
import FileDropZone from "@/components/ui/FileDropZone";
import ProcessTracker from "@/components/ui/ProcessTracker";
import ErrorSlidePanel from "@/components/ui/ErrorSlidePanel";
import {
  useUploadFiles,
  useIngestionStatus,
  useIngestionErrors,
  useIngestionHistory,
} from "@/hooks/useIngestion";
import type { UploadResult } from "@/hooks/useIngestion";

function statusBadgeFn(s: string) {
  const map: Record<string, string> = {
    completed: "✅",
    processing: "🔄",
    pending: "⏳",
    failed: "❌",
    quarantined: "⚠️",
  };
  return map[s.toLowerCase()] || "❓";
}

interface QueuedFile {
  name: string;
  size: number;
  file: File;
}

export default function UploadPage() {
  const [queuedFiles, setQueuedFiles] = useState<QueuedFile[]>([]);
  const [uploadResults, setUploadResults] = useState<UploadResult[]>([]);
  const [activeIds, setActiveIds] = useState<string[]>([]);
  const [errorPanel, setErrorPanel] = useState<{ open: boolean; filename: string; ingestionId: string | null }>({
    open: false, filename: "", ingestionId: null,
  });
  const [toasts, setToasts] = useState<{ id: string; message: string }[]>([]);

  const uploadMutation = useUploadFiles();
  const historyQuery = useIngestionHistory();

  const addToast = (message: string) => {
    const id = Date.now().toString();
    setToasts((prev) => [...prev, { id, message }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 6000);
  };

  const handleFilesAdded = useCallback((files: File[]) => {
    setQueuedFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name));
      const newFiles = files.filter((f) => !existing.has(f.name));
      return [...prev, ...newFiles.map((f) => ({ name: f.name, size: f.size, file: f }))];
    });
  }, []);

  const handleRemoveFile = (index: number) => {
    setQueuedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleClearAll = () => setQueuedFiles([]);

  const handleUpload = async () => {
    if (!queuedFiles.length || uploadMutation.isPending) return;

    const result = await uploadMutation.mutateAsync(queuedFiles.map((f) => f.file));
    const results = result.results || [];
    setUploadResults(results);
    setQueuedFiles([]);

    const ids = results.filter((r) => r.ingestion_id).map((r) => r.ingestion_id!);
    setActiveIds((prev) => [...prev, ...ids]);

    result.rejected?.forEach((r) => addToast(`⚠️ ${r.filename}: ${r.reason}`));
  };

  const handleViewFailures = (filename: string, ingestionId: string | null) => {
    setErrorPanel({ open: true, filename, ingestionId });
  };

  const historyRows = historyQuery.data || [];

  return (
    <motion.div
      className="p-6 space-y-5"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
    >
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-text-primary">File Upload & Ingestion</h1>
        <p className="text-sm text-text-secondary mt-0.5">
          Upload Excel files to process into the database
        </p>
      </div>

      {/* Drop zone */}
      <FileDropZone
        files={queuedFiles}
        onFilesAdded={handleFilesAdded}
        onRemoveFile={handleRemoveFile}
        onClearAll={handleClearAll}
        uploading={uploadMutation.isPending}
      />

      {/* Upload button */}
      {queuedFiles.length > 0 && (
        <div className="flex items-center gap-3">
          <button
            onClick={handleUpload}
            disabled={uploadMutation.isPending}
            className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-accent rounded-btn hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            <Upload size={16} />
            {uploadMutation.isPending ? "Uploading..." : `Upload ${queuedFiles.length} file${queuedFiles.length > 1 ? "s" : ""}`}
          </button>
        </div>
      )}

      {/* Processing */}
      {activeIds.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">
            Processing
          </h3>
          <div className="space-y-3">
            {uploadResults.map((r) => (
              <ProcessingTrackerWrapper
                key={r.ingestion_id || r.original_filename}
                result={r}
                onViewFailures={handleViewFailures}
                onQuarantine={(msg) => addToast(msg)}
              />
            ))}
          </div>
        </div>
      )}

      {/* History */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
            Upload History
          </h3>
          <button
            onClick={() => historyQuery.refetch()}
            className="flex items-center gap-1 text-xs text-text-muted hover:text-text-secondary transition-colors"
          >
            <RotateCcw size={12} />
            Refresh
          </button>
        </div>

        {historyQuery.isLoading ? (
          <div className="space-y-2 animate-pulse">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-12 bg-nav-hover rounded-btn" />
            ))}
          </div>
        ) : historyRows.length === 0 ? (
          <div className="card-container p-8 text-center">
            <p className="text-sm text-text-muted">No upload history</p>
            <p className="text-xs text-text-muted mt-1">
              Uploaded files and their processing status will appear here
            </p>
          </div>
        ) : (
          <div className="card-container overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-divider">
                  <th className="text-left px-4 py-2.5 text-xs text-text-muted font-semibold uppercase">Filename</th>
                  <th className="text-left px-4 py-2.5 text-xs text-text-muted font-semibold uppercase">Type</th>
                  <th className="text-left px-4 py-2.5 text-xs text-text-muted font-semibold uppercase">Status</th>
                  <th className="text-left px-4 py-2.5 text-xs text-text-muted font-semibold uppercase">When</th>
                  <th className="text-left px-4 py-2.5 text-xs text-text-muted font-semibold uppercase">Details</th>
                </tr>
              </thead>
              <tbody>
                {historyRows.map((row: any) => (
                  <tr key={row.id} className="border-b border-divider last:border-0 hover:bg-nav-hover transition-colors">
                    <td className="px-4 py-2.5 text-text-primary max-w-[200px] truncate" title={row.normalized_filename || row.original_filename}>
                      {row.normalized_filename || row.original_filename}
                    </td>
                    <td className="px-4 py-2.5 text-text-secondary">{row.report_type || "—"}</td>
                    <td className="px-4 py-2.5">
                      <span className="text-xs">{statusBadgeFn(row.status)} {row.status}</span>
                    </td>
                    <td className="px-4 py-2.5 text-text-muted text-xs">
                      {row.created_at ? new Date(row.created_at).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-2.5">
                      {row.status === "failed" && row.error_context?.fatal_error && (
                        <button
                          onClick={() => handleViewFailures(row.normalized_filename || row.original_filename, row.id)}
                          className="text-xs text-danger hover:underline"
                        >
                          View error
                        </button>
                      )}
                      {row.status === "quarantined" && row.error_context?.reason && (
                        <span className="text-xs text-[#D97706]" title={row.error_context.reason}>
                          {row.error_context.reason}
                        </span>
                      )}
                      {row.status === "completed" && (
                        <button
                          onClick={() => handleViewFailures(row.normalized_filename || row.original_filename, row.id)}
                          className="text-xs text-info hover:underline"
                        >
                          View details
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Error slide panel */}
      <ErrorSlidePanel
        open={errorPanel.open}
        onClose={() => setErrorPanel({ ...errorPanel, open: false })}
        filename={errorPanel.filename}
        rows={errorPanel.ingestionId ? ([] as FailedRow[]) : []}
      >
        {errorPanel.ingestionId && <ErrorPanelContent ingestionId={errorPanel.ingestionId} />}
      </ErrorSlidePanel>

      {/* Toasts */}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {toasts.map((t) => (
          <motion.div
            key={t.id}
            className="px-4 py-2.5 bg-[#FEF3C7] border border-[#FCD34D] rounded-card text-sm text-[#D97706] shadow-subtle max-w-sm"
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 50 }}
          >
            {t.message}
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}

/* ── Sub-components ─────────────────────────────────────────────────────── */

function ProcessingTrackerWrapper({
  result,
  onViewFailures,
  onQuarantine,
}: {
  result: UploadResult;
  onViewFailures: (filename: string, id: string | null) => void;
  onQuarantine: (msg: string) => void;
}) {
  const enabled = !!result.ingestion_id && result.status !== "classification_failed";
  const { data: status } = useIngestionStatus(result.ingestion_id, enabled);

  const filename = result.normalized_filename || result.original_filename;
  const dbStatus = status?.db_status || result.status;

  const steps = buildSteps(dbStatus);
  const isQuarantined = dbStatus === "quarantined";
  const isDone = dbStatus === "completed" || dbStatus === "failed" || isQuarantined;

  // Extract summary from error_context
  const ctx = status?.error_context || {};
  const loadResults = ctx.load_results || {};
  let successCount: number | undefined;
  let failedCount: number | undefined;

  if (typeof loadResults === "object" && !Array.isArray(loadResults)) {
    successCount = 0;
    failedCount = 0;
    for (const v of Object.values(loadResults)) {
      if (typeof v === "object" && v !== null && "success" in v) {
        successCount += (v as any).success || 0;
        failedCount += (v as any).failed || 0;
      }
    }
  }
  if (ctx.total_successes !== undefined) successCount = ctx.total_successes;
  if (ctx.total_failures !== undefined) failedCount = ctx.total_failures;

  // Quarantine toast
  const toastedRef = useRef(false);
  if (isQuarantined && !toastedRef.current) {
    toastedRef.current = true;
    const reason = ctx.reason || "Unknown reason";
    onQuarantine(`⚠️ ${filename} was quarantined — ${reason}`);
  }

  return (
    <ProcessTracker
      filename={filename}
      steps={steps}
      progress={status?.progress?.total ? ((status.progress.current || 0) / status.progress.total) * 100 : undefined}
      successCount={isDone ? successCount : undefined}
      failedCount={isDone ? failedCount : undefined}
      onViewFailures={() => onViewFailures(filename, result.ingestion_id)}
      errorMessage={dbStatus === "failed" ? ctx.fatal_error : undefined}
      quarantineReason={isQuarantined ? ctx.reason : undefined}
    />
  );
}

function buildSteps(dbStatus: string): { key: string; label: string; status: "pending" | "active" | "done" | "error" }[] {
  const base: { key: string; label: string; status: "pending" | "active" | "done" | "error" }[] = [
    { key: "received", label: "File received", status: "done" },
    { key: "classified", label: "Classified", status: "done" },
    { key: "routed", label: "Routed to folder", status: "done" },
  ];

  if (dbStatus === "pending") {
    base[2].status = "active";
    return [...base, { key: "processing", label: "Waiting to process", status: "pending" as const }];
  }

  if (dbStatus === "processing") {
    return [...base, { key: "processing", label: "Processing data...", status: "active" as const }];
  }

  if (dbStatus === "completed") {
    return [...base, { key: "processing", label: "Processing complete", status: "done" as const }];
  }

  if (dbStatus === "failed") {
    return [...base, { key: "processing", label: "Processing failed", status: "error" as const }];
  }

  if (dbStatus === "quarantined") {
    base[1].status = "error";
    return [...base.slice(0, 2), { key: "processing", label: "Quarantined", status: "error" as const }];
  }

  if (dbStatus === "classification_failed") {
    base[0].status = "done";
    base[1].status = "error";
    return base.slice(0, 2);
  }

  return [...base, { key: "processing", label: "Processing...", status: "active" as const }];
}

function ErrorPanelContent({ ingestionId }: { ingestionId: string }) {
  const errorsQuery = useIngestionErrors(ingestionId);

  if (!errorsQuery.isFetched) {
    // trigger fetch
    errorsQuery.refetch();
  }

  return (
    <>
      {errorsQuery.isLoading && (
        <div className="p-5 space-y-3 animate-pulse">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-10 bg-nav-hover rounded-btn" />
          ))}
        </div>
      )}
      {errorsQuery.data && errorsQuery.data.total_failed === 0 && (
        <div className="flex flex-col items-center justify-center h-full py-12 text-text-muted">
          <p className="text-sm">No failure details available</p>
        </div>
      )}
      {errorsQuery.data && errorsQuery.data.failed_rows.length > 0 && (
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-surface border-b border-divider">
            <tr>
              <th className="text-left px-4 py-2.5 text-text-muted font-semibold uppercase w-14">Row</th>
              <th className="text-left px-4 py-2.5 text-text-muted font-semibold uppercase w-20">ID No</th>
              <th className="text-left px-4 py-2.5 text-text-muted font-semibold uppercase w-24">Field</th>
              <th className="text-left px-4 py-2.5 text-text-muted font-semibold uppercase">Message</th>
            </tr>
          </thead>
          <tbody>
            {errorsQuery.data.failed_rows.map((r, i) => (
              <tr key={i} className="border-b border-divider last:border-0 hover:bg-nav-hover transition-colors">
                <td className="px-4 py-2 text-text-secondary">{r.row}</td>
                <td className="px-4 py-2 text-text-primary font-medium">{r.id_no}</td>
                <td className="px-4 py-2 text-text-secondary">{r.field}</td>
                <td className="px-4 py-2 text-text-primary">{r.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
