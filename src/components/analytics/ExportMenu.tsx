import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Download, FileDown, Loader2, Send } from "lucide-react";
import { exportToCSV } from "@/lib/csvExport";
import { sendToReportBuilder, type DateRangeLike } from "@/lib/reportInbox";
import { useToast } from "@/components/ui/Toast";

/** Row descriptor feeding Export CSV + Send to Report. */
export interface ExportMenuDescriptor {
  /** Rows for both actions (sync or full-fetch promise). */
  getRows: () => Record<string, unknown>[] | Promise<Record<string, unknown>[]>;
  /** Base file/chart name (backend adds its timestamp suffix for inbox). */
  fileName: string;
  dateRange?: DateRangeLike;
  /** Inbox source label (defaults to fileName). */
  source?: string;
}

interface ExportMenuProps extends ExportMenuDescriptor {
  /** Icon-only (default) or labeled button trigger. */
  variant?: "icon" | "button";
  label?: string;
  className?: string;
}

/** Export control: same Download look, but offers Export CSV + Send to Report. */
export default function ExportMenu({
  getRows,
  fileName,
  dateRange,
  source,
  variant = "icon",
  label = "Export",
  className = "",
}: ExportMenuProps) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<null | "csv" | "send">(null);
  const closeTimer = useRef<number | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  const { toast } = useToast();
  const qc = useQueryClient();

  const scheduleClose = () => {
    if (closeTimer.current) window.clearTimeout(closeTimer.current);
    closeTimer.current = window.setTimeout(() => setOpen(false), 150);
  };
  const cancelClose = () => {
    if (closeTimer.current) {
      window.clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  };

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open ]);

  useEffect(() => () => {
    if (closeTimer.current) window.clearTimeout(closeTimer.current);
  }, []);

  const resolveRows = async (): Promise<Record<string, unknown>[] | null> => {
    try {
      const rows = await getRows();
      if (!rows || rows.length === 0) {
        toast("Nothing to export — no rows", "warning");
        return null;
      }
      return rows;
    } catch {
      toast("Could not gather rows for export", "error");
      return null;
    }
  };

  const doCSV = async () => {
    if (busy) return;
    setBusy("csv");
    try {
      const rows = await resolveRows();
      if (rows) exportToCSV(rows as Record<string, any>[], fileName, dateRange);
    } finally {
      setBusy(null);
      setOpen(false);
    }
  };

  const doSend = async () => {
    if (busy) return;
    setBusy("send");
    try {
      const rows = await resolveRows();
      if (!rows) return;
      const saved = await sendToReportBuilder(rows, fileName, source || fileName, dateRange);
      await qc.invalidateQueries({ queryKey: ["report-inbox"] });
      toast(`Sent to Report Builder (${saved.row_count.toLocaleString()} rows)`, "success");
    } catch {
      toast("Could not send to Report Builder — check the API server", "error");
    } finally {
      setBusy(null);
      setOpen(false);
    }
  };

  const itemCls =
    "w-full flex items-center gap-2 px-3 py-2 text-left text-xs text-text-primary hover:bg-nav-hover transition-colors disabled:opacity-50";

  return (
    <div
      ref={ref}
      className={`relative ${className}`}
      onMouseEnter={() => { cancelClose(); setOpen(true); }}
      onMouseLeave={scheduleClose}
    >
      {variant === "button" ? (
        <button
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs border border-border rounded-btn transition-colors text-text-secondary hover:bg-nav-hover"
          title="Export options"
        >
          <Download size={12} />
          {label}
          <ChevronDown size={11} className={open ? "rotate-180 transition-transform" : "transition-transform"} />
        </button>
      ) : (
        <button
          onClick={() => setOpen((v) => !v)}
          title="Export options"
          aria-label="Export options"
          className="p-2 rounded-btn text-text-muted hover:text-accent hover:bg-nav-hover transition-colors flex-shrink-0"
        >
          <Download size={14} />
        </button>
      )}

      {open && (
        <div className="absolute right-0 top-full mt-1 z-50 w-44 bg-surface border border-border rounded-card shadow-lg overflow-hidden py-1">
          <button onClick={() => { void doCSV(); }} disabled={busy !== null} className={itemCls}>
            {busy === "csv" ? <Loader2 size={13} className="animate-spin" /> : <FileDown size={13} className="text-text-muted" />}
            Export CSV
          </button>
          <button onClick={() => { void doSend(); }} disabled={busy !== null} className={itemCls}>
            {busy === "send" ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} className="text-text-muted" />}
            Send to Report
          </button>
        </div>
      )}
    </div>
  );
}
