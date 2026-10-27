import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, FileSpreadsheet, X } from "lucide-react";
import { useFileFormats } from "@/hooks/useIngestion";
import type { ColumnUsage, FileFormatSpec } from "@/lib/fileSchema";

interface FileFormatGuideProps {
  open: boolean;
  onClose: () => void;
}

const USAGE: Record<ColumnUsage, { label: string; text: string; dot: string }> = {
  required: { label: "Required", text: "text-badge-green-text", dot: "bg-success" },
  optional: { label: "Optional", text: "text-badge-amber-text", dot: "bg-warning" },
  ignored: { label: "Not used", text: "text-text-muted", dot: "bg-divider" },
};

function headerRule(spec: FileFormatSpec): string {
  if (spec.header_rows > 1) {
    return `Rows 1 and 2 are headers (group row, then column row). Data starts on row ${
      spec.data_starts_row
    }.`;
  }
  return `Row 1 is the column header. Data starts on row ${spec.data_starts_row}.`;
}

export default function FileFormatGuide({ open, onClose }: FileFormatGuideProps) {
  const { data, isLoading, isError } = useFileFormats(open);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [showIgnored, setShowIgnored] = useState(false);

  const types = data?.types ?? [];
  const active = types.find((t) => t.id === activeId) ?? types[0];

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return createPortal(
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            key="backdrop"
            className="fixed inset-0 bg-black/20 z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            key="panel"
            role="dialog"
            aria-modal="true"
            aria-label="File formats"
            className="fixed inset-y-0 right-0 z-50 flex h-screen max-h-screen w-[560px] max-w-[94vw] flex-col overflow-hidden bg-surface border-l border-border"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={{ type: "spring", damping: 26, stiffness: 220 }}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-divider flex-shrink-0">
          <div>
            <h3 className="text-sm font-semibold text-text-primary">File formats</h3>
            <p className="text-xs text-text-muted mt-0.5">
              {data?.note ?? "How each upload file must be laid out."}
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close file formats"
            className="p-1.5 rounded-btn hover:bg-nav-hover text-text-muted hover:text-text-secondary"
          >
            <X size={18} />
          </button>
        </div>

        <div
          role="tablist"
          className="flex gap-1 px-5 pt-3 border-b border-divider overflow-x-auto flex-shrink-0"
        >
          {types.map((type) => (
            <button
              key={type.id}
              role="tab"
              aria-selected={active?.id === type.id}
              onClick={() => setActiveId(type.id)}
              className={`px-3 py-2 text-xs font-medium whitespace-nowrap border-b-2 transition-colors ${
                active?.id === type.id
                  ? "border-accent text-text-primary"
                  : "border-transparent text-text-muted hover:text-text-secondary"
              }`}
            >
              {type.label}
            </button>
          ))}
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto overscroll-contain px-5 pt-4 pb-10 space-y-4">
          {isLoading ? (
            <div className="space-y-3 animate-pulse">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="h-5 bg-nav-hover rounded" />
              ))}
            </div>
          ) : isError || !active ? (
            <div className="card-container p-4 text-sm text-danger">
              Could not load the file formats. Close this panel and try again.
            </div>
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-2 text-[11px]">
                <span className="flex items-center gap-1 px-2 py-1 rounded-full bg-nav-hover text-text-secondary">
                  <FileSpreadsheet size={12} />
                  {active.accepted} only
                </span>
                {active.min_columns != null && (
                  <span className="px-2 py-1 rounded-full bg-nav-hover text-text-secondary">
                    {active.min_columns}+ columns
                  </span>
                )}
                <span className="px-2 py-1 rounded-full bg-nav-hover text-text-secondary">
                  {active.positional ? "Position matters" : "Matched by header name"}
                </span>
              </div>

              <div className="card-container p-3 space-y-1">
                <p className="text-xs text-text-primary font-medium">{headerRule(active)}</p>
                <p className="text-[11px] text-text-muted">
                  Saved as <span className="font-mono">{active.filename_example}</span>
                </p>
              </div>

              {active.warnings.map((warning) => (
                <div
                  key={warning}
                  className="flex items-start gap-2 px-3 py-2 rounded-input bg-badge-amber-bg border border-warning/30 text-[11px] text-badge-amber-text"
                >
                  <AlertTriangle size={13} className="mt-0.5 flex-shrink-0" />
                  <span>{warning}</span>
                </div>
              ))}

              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
                    Columns
                  </p>
                  <button
                    onClick={() => setShowIgnored((v) => !v)}
                    className="text-[11px] text-text-muted hover:text-text-secondary"
                  >
                    {showIgnored ? "Hide unused columns" : "Show unused columns"}
                  </button>
                </div>

                {active.required_headers && active.required_headers.length > 0 && (
                  <p className="text-[11px] text-text-secondary mb-2">
                    Required headers (any order):{" "}
                    <span className="font-mono text-text-primary">
                      {active.required_headers.join(", ")}
                    </span>
                  </p>
                )}

                <div className="border border-divider rounded-card overflow-hidden">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-nav-hover text-text-muted">
                        <th className="text-left px-3 py-2 font-semibold w-14">
                          {active.positional ? "Col" : "—"}
                        </th>
                        <th className="text-left px-3 py-2 font-semibold">Header</th>
                        <th className="text-left px-3 py-2 font-semibold w-24">Use</th>
                      </tr>
                    </thead>
                    <tbody>
                      {active.columns
                        .filter((c) => showIgnored || c.usage !== "ignored")
                        .map((column, i) => {
                          const usage = USAGE[column.usage];
                          return (
                            <tr
                              key={`${column.index ?? "h"}-${column.header}-${i}`}
                              className="border-t border-divider align-top"
                            >
                              <td className="px-3 py-1.5 font-mono text-text-muted">
                                {column.index == null ? "—" : column.index}
                              </td>
                              <td className="px-3 py-1.5">
                                <p className="text-text-primary font-medium">
                                  {column.header}
                                </p>
                                {column.group && (
                                  <p className="text-[10px] text-text-muted">
                                    group: {column.group}
                                  </p>
                                )}
                                {column.note && (
                                  <p className="text-[10px] text-text-muted">{column.note}</p>
                                )}
                              </td>
                              <td className={`px-3 py-1.5 ${usage.text}`}>
                                <span className="inline-flex items-center gap-1.5">
                                  <span className={`w-1.5 h-1.5 rounded-full ${usage.dot}`} />
                                  {usage.label}
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>,
    document.body
  );
}
