import { motion, AnimatePresence } from "framer-motion";
import { X, Clock, Database, ShieldCheck } from "lucide-react";
import type { IngestionDetails } from "@/hooks/useIngestion";

interface ErrorSlidePanelProps {
  open: boolean;
  onClose: () => void;
  filename: string;
  details?: IngestionDetails | null;
  detailsLoading?: boolean;
  children?: React.ReactNode;
}

function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-GB") + " " +
    new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

export default function ErrorSlidePanel({
  open,
  onClose,
  filename,
  details,
  detailsLoading,
  children,
}: ErrorSlidePanelProps) {
  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 bg-black/20 z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            className="fixed right-0 top-0 h-full w-[460px] max-w-[90vw] bg-surface border-l border-border z-50 flex flex-col"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-divider flex-shrink-0">
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-text-primary truncate">Processing Details</h3>
                <p className="text-xs text-text-secondary truncate">{filename}</p>
              </div>
              <button
                onClick={onClose}
                className="p-1.5 rounded-btn hover:bg-nav-hover text-text-muted hover:text-text-secondary transition-colors flex-shrink-0"
              >
                <X size={18} />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto">
              {children ? (
                children
              ) : detailsLoading && (
                <div className="space-y-3 animate-pulse">
                  <div className="grid grid-cols-3 gap-2">
                    {[...Array(3)].map((_, i) => (<div key={i} className="h-16 bg-nav-hover rounded-card" />))}
                  </div>
                  {[...Array(5)].map((_, i) => (<div key={i} className="h-8 bg-nav-hover rounded-btn" />))}
                </div>
              )}

              {!detailsLoading && details && (
                <>
                  {/* Meta */}
                  <div>
                    <span
                      className={`inline-block text-xs px-2.5 py-1 rounded-full font-medium ${
                        details.status === "completed"
                          ? "bg-badge-green-bg text-badge-green-text"
                          : details.status === "failed"
                          ? "bg-badge-red-bg text-badge-red-text"
                          : "bg-badge-amber-bg text-badge-amber-text"
                      }`}
                    >
                      {details.status}
                    </span>
                    <p className="text-xs text-text-muted mt-2">
                      {details.report_type || "Unknown type"}
                    </p>
                  </div>

                  {/* Stat chips */}
                  <div className="grid grid-cols-3 gap-2">
                    <div className="border border-border rounded-card p-3 text-center">
                      <Database size={14} className="mx-auto text-success mb-1" />
                      <p className="text-lg font-bold text-success leading-6">
                        {(details.summary.rows_loaded || 0).toLocaleString()}
                      </p>
                      <p className="text-[10px] text-text-muted uppercase">Rows Added</p>
                    </div>
                    <div className="border border-border rounded-card p-3 text-center">
                      <X size={14} className="mx-auto text-danger mb-1" />
                      <p className={`text-lg font-bold leading-6 ${(details.summary.rows_failed || 0) > 0 ? "text-danger" : "text-text-secondary"}`}>
                        {(details.summary.rows_failed || 0).toLocaleString()}
                      </p>
                      <p className="text-[10px] text-text-muted uppercase">Rows Failed</p>
                    </div>
                    <div className="border border-border rounded-card p-3 text-center">
                      <ShieldCheck size={14} className="mx-auto text-warning mb-1" />
                      <p className={`text-lg font-bold leading-6 ${(details.summary.validation_rejected || 0) > 0 ? "text-warning" : "text-text-secondary"}`}>
                        {(details.summary.validation_rejected || 0).toLocaleString()}
                      </p>
                      <p className="text-[10px] text-text-muted uppercase">Rejected</p>
                    </div>
                  </div>

                  {/* Timing */}
                  <div className="space-y-1.5 text-xs">
                    <div className="flex justify-between">
                      <span className="text-text-muted">Uploaded</span>
                      <span className="text-text-primary">{formatDate(details.created_at)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-muted">Processed</span>
                      <span className="text-text-primary">{formatDate(details.processed_at)}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-text-muted flex items-center gap-1"><Clock size={11} /> Duration</span>
                      <span className="text-text-primary">{formatDuration(details.duration_seconds)}</span>
                    </div>
                  </div>

                  {/* Per-table breakdown */}
                  {details.tables_breakdown.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">
                        Database Tables Affected
                      </p>
                      <div className="border border-border rounded-card divide-y divide-divider">
                        {details.tables_breakdown.map((t) => (
                          <div key={t.table} className="flex items-center justify-between px-3 py-2">
                            <span className="text-xs text-text-primary font-mono truncate mr-2">{t.table}</span>
                            <span className="text-xs whitespace-nowrap flex-shrink-0">
                              <span className="text-success font-medium">+{t.rows_added.toLocaleString()}</span>
                              {t.rows_failed > 0 && (
                                <span className="text-danger font-medium ml-2">✕{t.rows_failed}</span>
                              )}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Processor report (Nominal / Leave) */}
                  {details.processor_report && (
                    <div>
                      <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">
                        Processor Report
                      </p>
                      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
                        {[
                          ["Rows read", details.processor_report.rows_read],
                          ["New inserts", details.processor_report.new_inserts],
                          ["Updates", details.processor_report.updates],
                          ["Successes", details.processor_report.successes],
                          ["Partial", details.processor_report.partial_successes],
                          ["Failures", details.processor_report.failures],
                        ].map(([label, value]) =>
                          value != null ? (
                            <div key={label as string} className="flex justify-between">
                              <span className="text-text-muted">{label}</span>
                              <span className="text-text-primary font-medium">
                                {Number(value).toLocaleString()}
                              </span>
                            </div>
                          ) : null
                        )}
                      </div>
                    </div>
                  )}
                </>
              )}

              {!detailsLoading && !details && (
                <div className="flex flex-col items-center justify-center h-full py-12 text-text-muted">
                  <p className="text-sm">No details available</p>
                </div>
              )}

              {/* Failures table */}
              {!detailsLoading && details && details.failed_rows.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">
                    Failed Rows ({details.failed_rows.length})
                  </p>
                  <div className="border border-border rounded-card overflow-hidden">
                    <table className="w-full text-xs">
                      <thead className="bg-nav-hover border-b border-divider">
                        <tr>
                          <th className="text-left px-3 py-2 text-text-muted font-semibold w-12">Row</th>
                          <th className="text-left px-3 py-2 text-text-muted font-semibold w-16">ID</th>
                          <th className="text-left px-3 py-2 text-text-muted font-semibold">Message</th>
                        </tr>
                      </thead>
                      <tbody>
                        {details.failed_rows.slice(0, 50).map((r, i) => (
                          <tr key={i} className="border-b border-divider last:border-0">
                            <td className="px-3 py-1.5 text-text-secondary">{r.row}</td>
                            <td className="px-3 py-1.5 text-text-primary font-medium">{r.id_no}</td>
                            <td className="px-3 py-1.5 text-text-primary">{r.message}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {details.failed_rows.length > 50 && (
                      <p className="px-3 py-2 text-[10px] text-text-muted">
                        Showing first 50 of {details.failed_rows.length}
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
