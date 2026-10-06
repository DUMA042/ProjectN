import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeftRight, ArrowRight, Cog, Download, FileSpreadsheet, Inbox, Trash2, Undo2, Wrench } from "lucide-react";
import {
  downloadInboxFile,
  unprocessedCount,
  useDeleteInboxFile,
  useMoveInboxFile,
  useReportInbox,
  type InboxFile,
} from "@/lib/reportInbox";
import { useToast } from "@/components/ui/Toast";
import AssistantChat from "@/components/reports/AssistantChat";
import BuildHashDialog from "@/components/reports/BuildHashDialog";
import BuildProgress from "@/components/reports/BuildProgress";
import BuildTopics from "@/components/reports/BuildTopics";
import ReportPreview from "@/components/reports/ReportPreview";
import StoredReports from "@/components/reports/StoredReports";
import ConfirmCard from "@/components/ui/ConfirmCard";
import {
  analyzeBuild,
  cancelBuild,
  configureBuild,
  fetchReportView,
  generateBuild,
  hashBuild,
  startBuild,
  useBuildJob,
  type BuildStartResult,
  type DetectedTopic,
  type HashMode,
  type RecommendedRange,
  type ReportView,
  type TopicChoice,
} from "@/lib/reportBuild";

function fmtBytes(n: number): string {
  if (!Number.isFinite(n) || n <= 0) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

function fmtSentAt(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso || "—";
  return d.toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function FileTable({
  files,
  emptyText,
  emptyHint,
  onDownload,
  onDelete,
  moveLabel,
  moveTitle,
  onMove,
  draggingId,
  onRowDragStart,
  onRowDragEnd,
}: {
  files: InboxFile[];
  emptyText: string;
  emptyHint: string;
  onDownload: (f: InboxFile) => void;
  onDelete: (f: InboxFile) => void;
  moveLabel: string;
  moveTitle: string;
  onMove: (f: InboxFile) => void;
  draggingId?: string | null;
  onRowDragStart?: (e: React.DragEvent, f: InboxFile) => void;
  onRowDragEnd?: () => void;
}) {
  if (files.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-text-muted gap-2 py-12">
        <Inbox size={32} strokeWidth={1.5} opacity={0.5} />
        <p className="text-sm font-medium text-text-primary">{emptyText}</p>
        <p className="text-xs">{emptyHint}</p>
      </div>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-divider text-left text-table-header text-text-muted uppercase tracking-wider">
            <th className="px-4 py-2.5 font-medium">File</th>
            <th className="px-4 py-2.5 font-medium">Type</th>
            <th className="px-4 py-2.5 font-medium">Source</th>
            <th className="px-4 py-2.5 font-medium text-right">Rows</th>
            <th className="px-4 py-2.5 font-medium text-right">Size</th>
            <th className="px-4 py-2.5 font-medium">Sent</th>
            <th className="px-4 py-2.5 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {files.map((f) => (
            <tr
              key={f.id}
              draggable={!!onRowDragStart}
              onDragStart={(e) => onRowDragStart?.(e, f)}
              onDragEnd={() => onRowDragEnd?.()}
              className={`border-b border-divider last:border-0 hover:bg-nav-hover transition-colors ${onRowDragStart ? "cursor-grab active:cursor-grabbing" : ""} ${draggingId === f.id ? "opacity-40" : ""}`}
            >
              <td className="px-4 py-2.5">
                <span className="flex items-center gap-2 min-w-0">
                  <FileSpreadsheet size={15} className="text-accent flex-shrink-0" />
                  <span className="text-text-primary font-medium truncate" title={f.display_name}>
                    {f.display_name}
                  </span>
                </span>
              </td>
              <td className="px-4 py-2.5 whitespace-nowrap">
                {f.classification === "individual" ? (
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-badge-blue-bg text-badge-blue-text">
                    Individual
                  </span>
                ) : (
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-nav-hover text-text-secondary">
                    Non-individual
                  </span>
                )}
              </td>
              <td className="px-4 py-2.5 text-text-secondary text-xs whitespace-nowrap">{f.source}</td>
              <td className="px-4 py-2.5 text-text-primary tabular-nums text-right">{f.row_count.toLocaleString()}</td>
              <td className="px-4 py-2.5 text-text-secondary tabular-nums text-right whitespace-nowrap">{fmtBytes(f.byte_size)}</td>
              <td className="px-4 py-2.5 text-text-secondary text-xs whitespace-nowrap">{fmtSentAt(f.sent_at)}</td>
              <td className="px-4 py-2.5">
                <span className="flex items-center justify-end gap-1">
                  <button
                    onClick={() => onMove(f)}
                    title={moveTitle}
                    aria-label={`${moveLabel}: ${f.display_name}`}
                    className="p-2 rounded-btn text-text-muted hover:text-accent hover:bg-nav-hover transition-colors"
                  >
                    {f.status === "build" ? <Undo2 size={14} /> : <ArrowRight size={14} />}
                  </button>
                  <button
                    onClick={() => onDownload(f)}
                    title="Download this file"
                    aria-label={`Download ${f.display_name}`}
                    className="p-2 rounded-btn text-text-muted hover:text-accent hover:bg-nav-hover transition-colors"
                  >
                    <Download size={14} />
                  </button>
                  <button
                    onClick={() => onDelete(f)}
                    title="Delete this file"
                    aria-label={`Delete ${f.display_name}`}
                    className="p-2 rounded-btn text-text-muted hover:text-danger hover:bg-nav-hover transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Slim build queue: file name, time it entered the build section, and
 *  per-row Return-to-inbox + Process + Download actions. Draggable for
 *  drop-back. A hashed copy (if one exists) lives inside the same row,
 *  hidden behind a toggle — it never becomes a separate row. */
function BuildTable({
  files,
  emptyText,
  emptyHint,
  onReturn,
  onProcess,
  onDownload,
  hashedBy,
  draggingId,
  onRowDragStart,
  onRowDragEnd,
}: {
  files: InboxFile[];
  emptyText: string;
  emptyHint: string;
  onReturn: (f: InboxFile) => void;
  onProcess: (f: InboxFile) => void;
  onDownload: (f: InboxFile) => void;
  hashedBy: Map<string, InboxFile>;
  draggingId?: string | null;
  onRowDragStart?: (e: React.DragEvent, f: InboxFile) => void;
  onRowDragEnd?: () => void;
}) {
  const [showHashed, setShowHashed] = useState<Record<string, boolean>>({});
  if (files.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-text-muted gap-2 py-12">
        <Inbox size={32} strokeWidth={1.5} opacity={0.5} />
        <p className="text-sm font-medium text-text-primary">{emptyText}</p>
        <p className="text-xs">{emptyHint}</p>
      </div>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-divider text-left text-table-header text-text-muted uppercase tracking-wider">
            <th className="px-4 py-2.5 font-medium">File</th>
            <th className="px-4 py-2.5 font-medium">Moved in</th>
            <th className="px-4 py-2.5 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {files.map((f) => {
            const hashed = hashedBy.get(f.id);
            const viewing = showHashed[f.id] && hashed ? hashed : f;
            return (
            <tr
              key={f.id}
              draggable={!!onRowDragStart}
              onDragStart={(e) => onRowDragStart?.(e, f)}
              onDragEnd={() => onRowDragEnd?.()}
              className={`border-b border-divider last:border-0 hover:bg-nav-hover transition-colors ${onRowDragStart ? "cursor-grab active:cursor-grabbing" : ""} ${draggingId === f.id ? "opacity-40" : ""}`}
            >
              <td className="px-4 py-2.5">
                <span className="flex items-center gap-2 min-w-0">
                  <FileSpreadsheet size={15} className="text-accent flex-shrink-0" />
                  <span className="text-text-primary font-medium truncate" title={viewing.display_name}>
                    {viewing.display_name}
                  </span>
                  {viewing.id !== f.id && (
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-badge-blue-bg text-badge-blue-text flex-shrink-0">
                      Hashed
                    </span>
                  )}
                </span>
              </td>
              <td className="px-4 py-2.5 text-text-secondary text-xs whitespace-nowrap">
                {viewing.moved_at ? fmtSentAt(viewing.moved_at) : "—"}
              </td>
              <td className="px-4 py-2.5">
                <span className="flex items-center justify-end gap-1">
                  {hashed && (
                    <button
                      onClick={() => setShowHashed((s) => ({ ...s, [f.id]: !s[f.id] }))}
                      title={showHashed[f.id] ? "Show original file" : "Show hashed version"}
                      aria-label={`${showHashed[f.id] ? "Show original" : "Show hashed version"}: ${f.display_name}`}
                      className="p-2 rounded-btn text-text-muted hover:text-accent hover:bg-nav-hover transition-colors"
                    >
                      <ArrowLeftRight size={14} />
                    </button>
                  )}
                  <button
                    onClick={() => onReturn(f)}
                    title="Move back to Inbox"
                    aria-label={`Move back to Inbox: ${f.display_name}`}
                    className="p-2 rounded-btn text-text-muted hover:text-accent hover:bg-nav-hover transition-colors"
                  >
                    <Undo2 size={14} />
                  </button>
                  <button
                    onClick={() => onProcess(f)}
                    title="Process this file"
                    aria-label={`Process ${f.display_name}`}
                    className="p-2 rounded-btn text-text-muted hover:text-accent hover:bg-nav-hover transition-colors"
                  >
                    <Cog size={14} />
                  </button>
                  <button
                    onClick={() => onDownload(viewing)}
                    title="Download this file"
                    aria-label={`Download ${viewing.display_name}`}
                    className="p-2 rounded-btn text-text-muted hover:text-accent hover:bg-nav-hover transition-colors"
                  >
                    <Download size={14} />
                  </button>
                </span>
              </td>
            </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function ReportsPage() {
  const inbox = useReportInbox();
  const deleteFile = useDeleteInboxFile();
  const moveFile = useMoveInboxFile();
  const { toast } = useToast();
  const files: InboxFile[] = inbox.data?.files || [];
  const newFiles = files.filter((f) => (f.status || "inbox") !== "build");
  // Hashed copies live inside their original's row (toggle) — never as rows.
  const hashedBy = new Map<string, InboxFile>();
  for (const f of files) {
    const src = f.source || "";
    if (src.startsWith("hashed:")) hashedBy.set(src.slice("hashed:".length), f);
  }
  const buildFiles = files.filter(
    (f) => f.status === "build" && !(f.source || "").startsWith("hashed:")
  );
  const pending = unprocessedCount(files);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [draggingFile, setDraggingFile] = useState<InboxFile | null>(null);
  const [dropTarget, setDropTarget] = useState<"inbox" | "build" | null>(null);
  const ghostRef = useRef<HTMLDivElement | null>(null);
  // Build pipeline state.
  const qc = useQueryClient();
  const [buildStart, setBuildStart] = useState<BuildStartResult | null>(null);
  const [hashBusy, setHashBusy] = useState(false);
  const [starting, setStarting] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);
  const buildJob = useBuildJob(jobId, polling);
  const [topicsData, setTopicsData] = useState<{
    topics: DetectedTopic[];
    recommended_range: RecommendedRange;
  } | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeFailed, setAnalyzeFailed] = useState(false);
  const [configuring, setConfiguring] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [reportView, setReportView] = useState<ReportView | null>(null);
  const autoAnalyzedFor = useRef<string | null>(null);

  const onDownload = async (f: InboxFile) => {
    try {
      await downloadInboxFile(f);
    } catch {
      toast("Could not download the file — check the API server", "error");
    }
  };

  const [pendingDelete, setPendingDelete] = useState<InboxFile | null>(null);
  const [deleting, setDeleting] = useState(false);

  const onDelete = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await deleteFile(pendingDelete.id);
      toast("File deleted", "success");
      setPendingDelete(null);
    } catch {
      toast("Could not delete the file", "error");
    } finally {
      setDeleting(false);
    }
  };

  /** Return an original (and its hashed copy, if any) to the Inbox. */
  const onReturnBoth = async (f: InboxFile) => {
    try {
      await moveFile(f.id, "inbox");
      const hashed = hashedBy.get(f.id);
      if (hashed) await moveFile(hashed.id, "inbox");
      toast("Moved back to Inbox", "success");
    } catch {
      toast("Could not move the file", "error");
    }
  };

  const onMove = async (f: InboxFile, status: "inbox" | "build") => {
    try {
      await moveFile(f.id, status);
      toast(
        status === "build" ? "Moved to Build section" : "Moved back to Inbox",
        "success"
      );
    } catch {
      toast("Could not move the file", "error");
    }
  };

  const onProcessPlaceholder = () => {
    toast("Processing comes later", "info");
  };

  const apiDetail = (err: unknown, fallback: string): string => {
    const e = err as { response?: { data?: { detail?: unknown } }; request?: unknown };
    if (e?.request && !e?.response) {
      return "No connection to the server — check your internet and retry. Nothing was lost.";
    }
    const detail = e?.response?.data?.detail;
    return typeof detail === "string" && detail ? detail : fallback;
  };

  const needOnline = (): boolean => {
    if (typeof navigator !== "undefined" && !navigator.onLine) {
      toast("You appear to be offline — reconnect and retry. The build waits where it is.", "error");
      return false;
    }
    return true;
  };

  /** Build button: inspect files; hashing dialog only when needed. */
  const onBuild = async () => {
    if (buildFiles.length === 0 || starting) return;
    setStarting(true);
    setTopicsData(null);
    setReportView(null);
    setRebuildInit(null);
    setAnalyzeFailed(false);
    autoAnalyzedFor.current = null;
    setJobId(null);
    try {
      const res = await startBuild(buildFiles.map((f) => f.id));
      setBuildStart(res);
      if (!res.needs_hashing) {
        await runHash(res.job_id, "names_only");
      }
    } catch (err) {
      toast(apiDetail(err, "Could not start the build"), "error");
      setStarting(false);
    }
  };

  const runHash = async (jid: string, mode: HashMode) => {
    setHashBusy(true);
    try {
      await hashBuild(jid, mode);
      setBuildStart(null);
      setJobId(jid);
      setPolling(true);
    } catch (err) {
      toast(apiDetail(err, "Hashing failed"), "error");
    } finally {
      setHashBusy(false);
      setStarting(false);
    }
  };

  // Settle the progress panel when validation completes or a file fails.
  useEffect(() => {
    const job = buildJob.data;
    if (!job || !polling) return;
    if (job.stage === "validated" || job.stage === "complete") {
      setPolling(false);
      void qc.invalidateQueries({ queryKey: ["report-inbox"] });
      if (job.stage === "validated") {
        toast("Files validated and ready", "success");
      } else if (!reportView) {
        // Reachable on every completion path (including a generation whose
        // POST outlived the client): always attach the preview + library.
        fetchReportView(job.id)
          .then((view) => {
            setReportView(view);
            void qc.invalidateQueries({ queryKey: ["report-builds"] });
          })
          .catch(() => toast("Report is ready but the preview failed to load", "error"));
      }
    } else if (job.stage === "topics_ready") {
      setPolling(false);
      const p = job.payload as {
        topics?: DetectedTopic[];
        recommended_range?: RecommendedRange;
      };
      if (p.topics && p.recommended_range) {
        setTopicsData({ topics: p.topics, recommended_range: p.recommended_range });
      }
    } else if (job.files.some((f) => f.state === "error")) {
      setPolling(false);
      const bad = job.files.find((f) => f.state === "error");
      toast(bad?.error || "A file failed validation", "error");
    }
  }, [buildJob.data, polling, generating, reportView, qc, toast]);

  /** Send validated files to the AI for topic detection. */
  const onAnalyze = async () => {
    if (!jobId || analyzing || !needOnline()) return;
    setAnalyzing(true);
    setAnalyzeFailed(false);
    setTopicsData(null);
    setPolling(true);
    try {
      const res = await analyzeBuild(jobId);
      setTopicsData({ topics: res.topics, recommended_range: res.recommended_range });
      toast(`${res.topics.length} report topics detected`, "success");
    } catch (err) {
      setAnalyzeFailed(true);
      toast(apiDetail(err, "AI analysis failed"), "error");
    } finally {
      setAnalyzing(false);
    }
  };

  // Auto-chain: run AI analysis once per job as soon as files validate,
  // so the user can never act on a stale stage. The button below is retry-only.
  useEffect(() => {
    const job = buildJob.data;
    if (!job || !polling || analyzing) return;
    if (job.stage === "validated" && !topicsData && autoAnalyzedFor.current !== job.id) {
      autoAnalyzedFor.current = job.id;
      void onAnalyze();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [buildJob.data, polling, topicsData, analyzing]);

  /** Cancel the running build: server stops work and cleans created files. */
  const [cancelling, setCancelling] = useState(false);
  const onCancelBuild = async () => {
    if (!jobId || cancelling) return;
    setCancelling(true);
    try {
      const res = await cancelBuild(jobId);
      setPolling(false);
      setTopicsData(null);
      setReportView(null);
      autoAnalyzedFor.current = null;
      void qc.invalidateQueries({ queryKey: ["report-inbox"] });
      void qc.invalidateQueries({ queryKey: ["report-builds"] });
      toast(
        res.removed_hashed > 0
          ? `Build cancelled — ${res.removed_hashed} created file(s) cleaned up`
          : "Build cancelled",
        "info"
      );
    } catch (err) {
      toast(apiDetail(err, "Could not cancel the build"), "error");
    } finally {
      setCancelling(false);
    }
  };

  /** Reopen the saved selection to edit topics/range and rebuild anew. */
  const [rebuildInit, setRebuildInit] = useState<{
    topics: TopicChoice[];
    range: { min_words: number; max_words: number };
  } | null>(null);
  const onRebuild = () => {
    const sel = (buildJob.data?.payload as {
      selection?: { topics: TopicChoice[]; word_range: { min_words: number; max_words: number } };
    } | undefined)?.selection;
    if (!sel) {
      toast("No saved configuration on this job", "error");
      return;
    }
    const detected = new Set((topicsData?.topics || []).map((t) => t.name));
    setRebuildInit({
      topics: sel.topics.filter((t) => detected.size === 0 || detected.has(t.name)),
      range: sel.word_range,
    });
    setReportView(null);
  };
  const onGenerate = async (topics: TopicChoice[], range: { min_words: number; max_words: number }) => {
    if (!jobId || configuring || generating || !needOnline()) return;
    setConfiguring(true);
    try {
      const fresh = await buildJob.refetch();
      const stage = fresh.data?.stage;
      if (stage !== "topics_ready") {
        if (stage === "generating") {
          toast("Report is already generating — track progress below", "info");
          setPolling(true);
        } else if (stage === "complete") {
          toast("This report is already complete", "info");
        } else {
          toast(`Files are at '${stage || "unknown"}' — run AI analysis first`, "error");
        }
        return;
      }
      await configureBuild(jobId, topics, range);
    } catch (err) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 409) {
        // Lost the race after a fresh check: something is already running.
        toast(apiDetail(err, "Report is already generating"), "info");
        setPolling(true);
      } else {
        toast(apiDetail(err, "Could not save the configuration"), "error");
      }
      return;
    } finally {
      setConfiguring(false);
    }
    setGenerating(true);
    setPolling(true);
    setReportView(null);
    try {
      await generateBuild(jobId);
      const view = await fetchReportView(jobId);
      setReportView(view);
      void qc.invalidateQueries({ queryKey: ["report-builds"] });
      toast("Report complete", "success");
    } catch (err) {
      toast(apiDetail(err, "Report generation failed"), "error");
    } finally {
      setGenerating(false);
    }
  };

  const clearDrag = () => {
    setDraggingId(null);
    setDraggingFile(null);
    setDropTarget(null);
  };

  /** Start a row drag with a compact custom ghost (icon + shortened name). */
  const beginRowDrag = (e: React.DragEvent, f: InboxFile) => {
    e.dataTransfer.setData("text/plain", f.id);
    e.dataTransfer.effectAllowed = "move";
    setDraggingId(f.id);
    setDraggingFile(f);
    // setDragImage snapshots synchronously, before React re-renders the
    // ghost — write the name imperatively so the snapshot is never stale.
    const label = ghostRef.current?.querySelector("[data-ghost-name]");
    if (label) label.textContent = f.display_name;
    if (ghostRef.current) {
      try {
        e.dataTransfer.setDragImage(ghostRef.current, 16, 16);
      } catch {
        /* older browsers fall back to the native row ghost */
      }
    }
  };

  /** Shared drop handler for both cards: move the dragged file into `status`. */
  const onDropTo = (e: React.DragEvent, status: "inbox" | "build") => {
    e.preventDefault();
    const id = e.dataTransfer.getData("text/plain");
    clearDrag();
    if (!id) return;
    const f = files.find((x) => x.id === id);
    if (!f) return;
    if ((f.status || "inbox") === status) return;
    void onMove(f, status);
  };

  const dropRing = (which: "inbox" | "build") =>
    dropTarget === which ? "ring-2 ring-accent ring-inset" : "";

  /** Full-card drop overlay: idle hint on both cards while dragging,
   *  strong accent treatment on the hovered card. pointer-events-none so
   *  the card underneath still receives the drop. */
  const renderDropOverlay = (which: "inbox" | "build", activeText: string, idleText: string) => {
    if (!draggingId) return null;
    const active = dropTarget === which;
    return (
      <div
        aria-hidden="true"
        className={`pointer-events-none absolute inset-0 z-10 flex items-center justify-center border-2 border-dashed ${
          active ? "border-accent bg-accent/10" : "border-text-muted/30"
        }`}
      >
        <span
          className={`px-3 py-1.5 rounded-full text-xs font-medium shadow ${
            active ? "bg-accent text-white" : "bg-surface text-text-secondary border border-border"
          }`}
        >
          {active ? activeText : idleText}
        </span>
      </div>
    );
  };

  return (
    <motion.div
      className="p-6 space-y-4"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Report Builder</h1>
          <p className="text-sm text-text-secondary mt-0.5">
            Files sent via “Send to Report” from any export button — stored in the system for later review.
          </p>
        </div>
        <button
          onClick={() => inbox.refetch()}
          className="px-3 py-1.5 text-xs border border-border rounded-btn bg-surface text-text-secondary hover:bg-nav-hover transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Files + assistant workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-[1.15fr_1fr] gap-4 items-start">
      <div className="space-y-4 min-w-0">
      {/* Inbox — new arrivals (drop target for drag-back from Build) */}
      <div
        className={`card-container overflow-hidden relative ${dropRing("inbox")}`}
        onDragOver={(e) => {
          if (!draggingId) return;
          e.preventDefault();
          e.dataTransfer.dropEffect = "move";
          setDropTarget("inbox");
        }}
        onDragLeave={() => setDropTarget((t) => (t === "inbox" ? null : t))}
        onDrop={(e) => onDropTo(e, "inbox")}
      >
        {renderDropOverlay("inbox", "Drop to move back to Inbox", "Drag here to return to Inbox")}
        <div className="px-4 pt-3 pb-1 flex items-center gap-2">
          <h2 className="text-xs font-semibold text-text-primary">Inbox</h2>
          {pending > 0 && (
            <span className="min-w-[20px] h-5 px-1 rounded-full bg-danger text-white text-[11px] font-bold inline-flex items-center justify-center tabular-nums">
              {pending > 99 ? "99+" : pending}
            </span>
          )}
        </div>
        {inbox.isLoading ? (
          <div className="p-5 space-y-2">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-9 bg-nav-hover rounded animate-pulse" />
            ))}
          </div>
        ) : (
          <FileTable
            files={newFiles}
            emptyText="Inbox is clear"
            emptyHint="Use “Send to Report” on any export button to collect files here."
            onDownload={onDownload}
            onDelete={(f) => setPendingDelete(f)}
            moveLabel="Move to Build"
            moveTitle="Move to Build section"
            onMove={(f) => { void onMove(f, "build"); }}
            draggingId={draggingId}
            onRowDragStart={beginRowDrag}
            onRowDragEnd={clearDrag}
          />
        )}
        {pendingDelete ? (
          <ConfirmCard
            title="Delete file?"
            message={`"${pendingDelete.display_name}" will be removed from the Report Builder. This cannot be undone.`}
            busy={deleting}
            onConfirm={() => { void onDelete(); }}
            onCancel={() => { if (!deleting) setPendingDelete(null); }}
          />
        ) : null}
      </div>

      {/* Build progress — overall stage + per-file trackers */}
      {jobId && buildJob.data ? (
        <BuildProgress
          job={buildJob.data}
          names={new Map(files.map((f) => [f.id, f.display_name]))}
          classifications={new Map(files.map((f) => [f.id, f.classification || "non_individual"]))}
          cancellable={!["complete", "cancelled"].includes(buildJob.data.stage) && !cancelling}
          onCancel={() => { void onCancelBuild(); }}
        />
      ) : null}

      {/* AI analysis retry — the first run chains automatically on validation */}
      {jobId && buildJob.data?.stage === "validated" && !topicsData && analyzeFailed && !analyzing ? (
        <button
          onClick={() => { void onAnalyze(); }}
          className="w-full px-3 py-2 text-xs font-medium text-white bg-accent rounded-btn hover:opacity-90 transition-opacity"
        >
          Retry AI analysis
        </button>
      ) : null}
      {jobId && analyzing ? (
        <div className="card-container px-4 py-3 flex items-center gap-2">
          <span className="w-3.5 h-3.5 rounded-full border-2 border-accent border-t-transparent animate-spin" />
          <p className="text-xs text-text-secondary">AI is reviewing the files… topics appear here when ready.</p>
        </div>
      ) : null}

      {/* Topic / focus / word-range selection */}
      {topicsData ? (
        <BuildTopics
          key={`${jobId || "nojobs"}-${rebuildInit ? "rebuild" : "fresh"}`}
          topics={topicsData.topics}
          recommended={topicsData.recommended_range}
          busy={configuring || generating}
          stageOk={buildJob.data?.stage === "topics_ready"}
          initialSelection={rebuildInit}
          onGenerate={(t, r) => { void onGenerate(t, r); }}
        />
      ) : null}

      {/* Edit & rebuild a finished report with new topics/range */}
      {jobId && buildJob.data?.stage === "complete" && topicsData ? (
        <button
          onClick={onRebuild}
          className="w-full px-3 py-2 text-xs font-medium border border-accent rounded-btn bg-transparent text-accent hover:bg-nav-hover transition-colors"
        >
          Edit topics & rebuild
        </button>
      ) : null}

      {/* Finished report preview + Word download */}
      {reportView ? <ReportPreview view={reportView} /> : null}

      {/* Library of all stored reports */}
      <StoredReports />

      {/* Build section — queued for report building (drop target for Inbox) */}
      <div
        className={`card-container overflow-hidden relative ${dropRing("build")}`}
        onDragOver={(e) => {
          if (!draggingId) return;
          e.preventDefault();
          e.dataTransfer.dropEffect = "move";
          setDropTarget("build");
        }}
        onDragLeave={() => setDropTarget((t) => (t === "build" ? null : t))}
        onDrop={(e) => onDropTo(e, "build")}
      >
        {renderDropOverlay("build", "Drop to move to Build", "Drag here to queue for Build")}
        <div className="px-4 pt-3 pb-1 flex items-center gap-2 flex-wrap">
          <Wrench size={13} className="text-text-muted" />
          <h2 className="text-xs font-semibold text-text-primary">Build section</h2>
          <span className="text-[11px] text-text-muted">Files queued for report building</span>
          <button
            onClick={() => { void onBuild(); }}
            title="Build the queued files"
            className="ml-auto px-3 py-1.5 text-xs font-medium border border-accent rounded-btn bg-transparent text-accent hover:bg-nav-hover transition-colors disabled:opacity-40"
            disabled={buildFiles.length === 0 || starting}
          >
            {starting ? "Starting…" : "Build"}
          </button>
        </div>
        {inbox.isLoading ? (
          <div className="p-5 space-y-2">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-9 bg-nav-hover rounded animate-pulse" />
            ))}
          </div>
        ) : (
          <BuildTable
            files={buildFiles}
            emptyText="Nothing queued for building"
            emptyHint="Drag files here from the Inbox, or use the arrow on a row."
            onReturn={(f) => { void onReturnBoth(f); }}
            onProcess={() => onProcessPlaceholder()}
            onDownload={onDownload}
            hashedBy={hashedBy}
            draggingId={draggingId}
            onRowDragStart={beginRowDrag}
            onRowDragEnd={clearDrag}
          />
        )}
      </div>
      </div>

      {/* Assistant — sticky on desktop, stacked below on narrow screens */}
      <div className="min-w-0 lg:sticky lg:top-4 lg:h-[calc(100vh-140px)] lg:min-h-[560px] h-[70vh]">
        <AssistantChat />
      </div>
      </div>

      {/* Hash choice dialog (individual files only) */}
      {buildStart?.needs_hashing ? (
        <BuildHashDialog
          files={buildStart.individual_files}
          warning={buildStart.hash_warning_names_and_ids}
          busy={hashBusy}
          onConfirm={(mode) => { void runHash(buildStart.job_id, mode); }}
          onCancel={() => { if (!hashBusy) setBuildStart(null); }}
        />
      ) : null}
      {/* Offscreen drag ghost (icon + shortened name); must stay rendered
          for setDragImage. Positioned off-viewport, never display:none. */}
      <div ref={ghostRef} aria-hidden="true" className="fixed left-0 top-[-200px] z-[9999] pointer-events-none">
        <div className="flex items-center gap-2 bg-surface border border-accent rounded-btn shadow-lg px-3 py-1.5">
          <FileSpreadsheet size={15} className="text-accent flex-shrink-0" />
          <span data-ghost-name className="text-xs font-medium text-text-primary max-w-[220px] truncate">
            {draggingFile?.display_name}
          </span>
        </div>
      </div>
    </motion.div>
  );
}
