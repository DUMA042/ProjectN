import { useState, useCallback, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, RotateCcw, Undo2, X } from "lucide-react";
import FileDropZone from "@/components/ui/FileDropZone";
import IngestionTrackerCard from "@/components/upload/IngestionTrackerCard";
import DetailsContent from "@/components/upload/DetailsContent";
import QuarantineExplorer from "@/components/upload/QuarantineExplorer";
import ErrorSlidePanel from "@/components/ui/ErrorSlidePanel";
import {
  useUploadFiles,
  useForgetIngestion,
  useIngestionHistory,
} from "@/hooks/useIngestion";

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

interface TrackerEntry {
  key: string;
  result: {
    ingestion_id: string | null;
    original_filename: string;
    normalized_filename?: string;
    report_type?: string;
    status: string;
  };
}

export default function UploadPage() {
  const [queuedFiles, setQueuedFiles] = useState<QueuedFile[]>([]);
  const [trackers, setTrackers] = useState<TrackerEntry[]>([]);
  const [detailsPanel, setDetailsPanel] = useState<{ open: boolean; ingestionId: string | null; filename: string }>({
    open: false, ingestionId: null, filename: "",
  });
  const [undoConfirm, setUndoConfirm] = useState<{ open: boolean; id: string; filename: string }>({
    open: false, id: "", filename: "",
  });
  const [toasts, setToasts] = useState<{ id: string; message: string; kind: "success" | "warning" | "error" | "info" }[]>([]);

  // History filters (#9)
  const [histType, setHistType] = useState("");
  const [histStatus, setHistStatus] = useState("");
  const [histSearch, setHistSearch] = useState("");

  // Drag-anywhere overlay (#11)
  const dragCounter = useRef(0);
  const [dragActive, setDragActive] = useState(false);

  const uploadMutation = useUploadFiles();
  const forgetMutation = useForgetIngestion();
  const historyQuery = useIngestionHistory();

  const addToast = (message: string, kind: "success" | "warning" | "error" | "info" = "info") => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setToasts((prev) => [...prev.slice(-4), { id, message, kind }]);
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

    // Optimistically clear the drop zone — files now live as tracker cards.
    setQueuedFiles([]);
    setTrackers(
      queuedFiles.map((f) => ({
        key: `pending-${f.name}-${Date.now()}`,
        result: { ingestion_id: null, original_filename: f.name, status: "uploading" },
      }))
    );

    try {
      const res = await uploadMutation.mutateAsync(queuedFiles.map((f) => f.file));
      // Replace placeholders with real results keyed by filename.
      setTrackers(
        (res.results || []).map((r) => ({
          key: r.ingestion_id || `fail-${r.original_filename}`,
          result: r,
        }))
      );
      res.rejected?.forEach((rj) => addToast(`⚠️ ${rj.filename}: ${rj.reason}`, "warning"));
    } catch {
      addToast("❌ Upload failed — check that the API server is running.", "error");
      setTrackers([]);
    }
  };

  const handleViewDetails = (filename: string, ingestionId: string | null) => {
    setDetailsPanel({ open: true, ingestionId, filename });
  };

  const handleTrackerCompleted = (filename: string, rowsLoaded: number) => {
    addToast(`✅ ${filename} processed — ${rowsLoaded.toLocaleString()} records loaded`, "success");
    // Auto-dismiss the tracker card after 3 seconds.
    setTimeout(() => {
      setTrackers((prev) => prev.filter((t) => t.result.original_filename !== filename && (t.result.normalized_filename || "") !== filename));
    }, 3000);
  };

  const handleTrackerQuarantined = (filename: string, reason: string) => {
    addToast(`⚠️ ${filename} was quarantined — ${reason}`, "warning");
  };

  const handleTrackerFailed = (filename: string, message: string) => {
    addToast(`❌ ${filename}: ${message}`, "error");
  };

  const handleDismissTracker = (key: string) => {
    setTrackers((prev) => prev.filter((t) => t.key !== key));
  };

  const handleUndoConfirm = async () => {
    if (!undoConfirm.id) return;
    try {
      const res = await forgetMutation.mutateAsync(undoConfirm.id);
      addToast(`✅ ${res.message}`, "success");
    } catch {
      addToast("❌ Could not remove the upload record.", "error");
    }
    setUndoConfirm({ open: false, id: "", filename: "" });
  };

  const historyRows = historyQuery.data || [];

  // ── #8: Rehydrate in-flight trackers across page refreshes ──────────────
  const rehydratedRef = useRef(false);
  useEffect(() => {
    if (rehydratedRef.current || !historyQuery.data) return;
    rehydratedRef.current = true;
    if (trackers.length > 0) return; // don't clobber live trackers
    const recent = (historyQuery.data as any[]).filter(
      (r) =>
        ["pending", "processing"].includes(r.status) &&
        r.created_at &&
        Date.now() - new Date(r.created_at).getTime() < 15 * 60 * 1000
    );
    if (recent.length) {
      setTrackers(
        recent.map((r) => ({
          key: r.id,
          result: {
            ingestion_id: r.id,
            original_filename: r.original_filename,
            normalized_filename: r.normalized_filename,
            report_type: r.report_type,
            status: r.status,
          },
        }))
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [historyQuery.data]);

  // ── #11: Drag-anywhere overlay ────────────────────────────────────────────
  useEffect(() => {
    const hasFiles = (e: DragEvent) =>
      Array.from(e.dataTransfer?.types || []).includes("Files");

    const onDragEnter = (e: DragEvent) => {
      if (!hasFiles(e)) return;
      e.preventDefault();
      dragCounter.current += 1;
      setDragActive(true);
    };
    const onDragLeave = (e: DragEvent) => {
      if (!hasFiles(e)) return;
      dragCounter.current -= 1;
      if (dragCounter.current <= 0) setDragActive(false);
    };
    const onDragOver = (e: DragEvent) => {
      if (hasFiles(e)) e.preventDefault();
    };
    const onDrop = (e: DragEvent) => {
      dragCounter.current = 0;
      setDragActive(false);
      if (!e.dataTransfer?.files?.length) return;
      e.preventDefault();
      const files = Array.from(e.dataTransfer.files).filter((f) =>
        f.name.toLowerCase().endsWith(".xlsx")
      );
      if (files.length) handleFilesAdded(files);
    };

    window.addEventListener("dragenter", onDragEnter);
    window.addEventListener("dragleave", onDragLeave);
    window.addEventListener("dragover", onDragOver);
    window.addEventListener("drop", onDrop);
    return () => {
      window.removeEventListener("dragenter", onDragEnter);
      window.removeEventListener("dragleave", onDragLeave);
      window.removeEventListener("dragover", onDragOver);
      window.removeEventListener("drop", onDrop);
    };
  }, [handleFilesAdded]);

  // ── #9: Client-side history filtering ────────────────────────────────────
  const histTypes = Array.from(
    new Set(historyRows.map((r: any) => r.report_type).filter(Boolean))
  ) as string[];
  const filteredHistory = historyRows.filter((r: any) => {
    if (histType && r.report_type !== histType) return false;
    if (histStatus && r.status !== histStatus) return false;
    if (histSearch) {
      const name = (r.normalized_filename || r.original_filename || "").toLowerCase();
      if (!name.includes(histSearch.toLowerCase())) return false;
    }
    return true;
  });

  const toastStyles: Record<string, string> = {
    success: "bg-badge-green-bg border-success/40 text-[#389E0D]",
    warning: "bg-badge-amber-bg border-warning/40 text-badge-amber-text",
    error: "bg-badge-red-bg border-danger/40 text-danger",
    info: "bg-surface border-border text-text-primary",
  };

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-text-primary">File Upload &amp; Ingestion</h1>
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
            className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-accent rounded-btn hover:bg-accent-hover disabled:opacity-50 transition-colors"
          >
            <Upload size={16} />
            {uploadMutation.isPending
              ? "Uploading…"
              : `Upload ${queuedFiles.length} file${queuedFiles.length > 1 ? "s" : ""}`}
          </button>
        </div>
      )}

      {/* Processing trackers */}
      <AnimatePresence>
        {trackers.length > 0 && (
          <div className="grid grid-cols-2 gap-4">
            {trackers.map((t) => (
              <motion.div
                key={t.key}
                layout
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.35 } }}
              >
                <IngestionTrackerCard
                  result={t.result}
                  onViewDetails={handleViewDetails}
                  onCompleted={handleTrackerCompleted}
                  onQuarantined={handleTrackerQuarantined}
                  onFailed={handleTrackerFailed}
                  onDismiss={() => handleDismissTracker(t.key)}
                />
              </motion.div>
            ))}
          </div>
        )}
      </AnimatePresence>

      {/* History */}
      <div>
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
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

        {/* Filters */}
        {historyRows.length > 0 && (
          <div className="card-container p-2.5 mb-3 flex items-center gap-2 flex-wrap">
            <input
              type="text"
              placeholder="Search filename…"
              value={histSearch}
              onChange={(e) => setHistSearch(e.target.value)}
              className="flex-1 min-w-[160px] max-w-[240px] px-3 py-1.5 text-xs border border-border rounded-input bg-surface text-text-primary placeholder-text-muted focus:outline-none focus:border-accent"
            />
            <select
              value={histType}
              onChange={(e) => setHistType(e.target.value)}
              className="px-2 py-1.5 text-xs border border-border rounded-input bg-surface text-text-secondary cursor-pointer"
            >
              <option value="">All Types</option>
              {histTypes.map((t) => (<option key={t} value={t}>{t}</option>))}
            </select>
            <select
              value={histStatus}
              onChange={(e) => setHistStatus(e.target.value)}
              className="px-2 py-1.5 text-xs border border-border rounded-input bg-surface text-text-secondary cursor-pointer"
            >
              <option value="">All Statuses</option>
              {["completed", "failed", "pending", "processing", "quarantined"].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            {(histType || histStatus || histSearch) && (
              <button
                onClick={() => { setHistType(""); setHistStatus(""); setHistSearch(""); }}
                className="text-xs text-text-muted hover:text-danger transition-colors"
              >
                Clear filters
              </button>
            )}
          </div>
        )}

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
                  <th className="text-left px-4 py-2.5 text-xs text-text-muted font-semibold uppercase">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredHistory.map((row: any) => (
                  <tr key={row.id} className="border-b border-divider last:border-0 hover:bg-nav-hover transition-colors group">
                    <td className="px-4 py-2.5 text-text-primary max-w-[220px] truncate" title={row.normalized_filename || row.original_filename}>
                      {row.normalized_filename || row.original_filename}
                    </td>
                    <td className="px-4 py-2.5 text-text-secondary">{row.report_type || "—"}</td>
                    <td className="px-4 py-2.5">
                      <span className="text-xs">{statusBadgeFn(row.status)} {row.status}</span>
                    </td>
                    <td className="px-4 py-2.5 text-text-muted text-xs whitespace-nowrap">
                      {row.created_at ? new Date(row.created_at).toLocaleDateString("en-GB") + " " + new Date(row.created_at).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }) : "—"}
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-3 opacity-60 group-hover:opacity-100 transition-opacity">
                        {(row.status === "completed" || row.status === "failed") && (
                          <button
                            onClick={() => handleViewDetails(row.normalized_filename || row.original_filename, row.id)}
                            className="text-xs text-info hover:underline"
                          >
                            View details
                          </button>
                        )}
                        <button
                          onClick={() => setUndoConfirm({
                            open: true,
                            id: row.id,
                            filename: row.normalized_filename || row.original_filename,
                          })}
                          disabled={forgetMutation.isPending}
                          title="Remove upload record so this file can be re-uploaded"
                          className="flex items-center gap-1 text-xs text-text-muted hover:text-danger transition-colors disabled:opacity-40"
                        >
                          <Undo2 size={12} />
                          Undo
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Details slide panel */}
      <ErrorSlidePanel
        open={detailsPanel.open}
        onClose={() => setDetailsPanel({ ...detailsPanel, open: false })}
        filename={detailsPanel.filename}
      >
        {detailsPanel.ingestionId && <DetailsContent ingestionId={detailsPanel.ingestionId} />}
      </ErrorSlidePanel>

      {/* Undo confirmation modal */}
      <AnimatePresence>
        {undoConfirm.open && (
          <>
            <motion.div
              className="fixed inset-0 bg-black/30 z-50"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setUndoConfirm({ open: false, id: "", filename: "" })}
            />
            <motion.div
              className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[420px] max-w-[90vw] bg-surface border border-border rounded-card z-50 p-5"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
            >
              <div className="flex items-start gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-badge-amber-bg flex items-center justify-center flex-shrink-0">
                  <Undo2 size={18} className="text-badge-amber-text" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-text-primary">Remove upload record?</h3>
                  <p className="text-xs text-text-secondary mt-1 leading-5">
                    The upload record for <span className="font-medium text-text-primary">{undoConfirm.filename}</span> will be removed,
                    allowing the same file to be uploaded again without a duplicate-content quarantine.
                  </p>
                  <p className="text-xs text-warning mt-2 font-medium">
                    Note: Data already loaded into the database by this file will remain.
                  </p>
                </div>
              </div>
              <div className="flex items-center justify-end gap-2">
                <button
                  onClick={() => setUndoConfirm({ open: false, id: "", filename: "" })}
                  className="px-4 py-2 text-sm border border-border rounded-btn text-text-secondary hover:bg-nav-hover transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleUndoConfirm}
                  disabled={forgetMutation.isPending}
                  className="px-4 py-2 text-sm font-medium text-white bg-accent rounded-btn hover:bg-accent-hover disabled:opacity-50 transition-colors"
                >
                  {forgetMutation.isPending ? "Removing…" : "Remove Record"}
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Quarantine Explorer */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
            Quarantine
          </h3>
        </div>
        <QuarantineExplorer onToast={addToast} />
      </div>

      {/* Drag-anywhere overlay (#11) */}
      <AnimatePresence>
        {dragActive && (
          <motion.div
            className="fixed inset-0 z-[70] bg-accent/10 backdrop-blur-sm pointer-events-none flex items-center justify-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div className="border-2 border-dashed border-accent bg-surface/95 rounded-card px-16 py-12 text-center">
              <Upload size={48} className="mx-auto mb-3 text-accent" strokeWidth={1.5} />
              <p className="text-base font-semibold text-text-primary">Drop files anywhere</p>
              <p className="text-xs text-text-secondary mt-1">.xlsx files will be added to the queue</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Toasts */}
      <div className="fixed top-4 right-4 z-[60] space-y-2 w-96 max-w-[90vw]">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              className={`flex items-start gap-2 px-4 py-3 border rounded-card text-sm shadow-layer-2 ${toastStyles[t.kind]}`}
              initial={{ opacity: 0, x: 60 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 60 }}
              transition={{ type: "spring", damping: 22, stiffness: 260 }}
            >
              <span className="flex-1">{t.message}</span>
              <button
                onClick={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))}
                className="opacity-50 hover:opacity-100 transition-opacity"
              >
                <X size={14} />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
