import { useState } from "react";
import { Download, FileText, Trash2 } from "lucide-react";
import { useStoredReports, useDeleteStoredReport } from "@/lib/reportBuild";
import { useToast } from "@/components/ui/Toast";
import ConfirmCard from "@/components/ui/ConfirmCard";

function fmtCreatedAt(iso: string): string {
  const d = new Date(iso);
  if (!iso || isNaN(d.getTime())) return "—";
  return d.toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Library of finished reports: stored server-side, downloadable, deletable. */
export default function StoredReports() {
  const library = useStoredReports();
  const remove = useDeleteStoredReport();
  const { toast } = useToast();
  const reports = library.data?.reports || [];
  const [pendingDelete, setPendingDelete] = useState<{ entry_id: string; label: string } | null>(null);
  const [deleting, setDeleting] = useState(false);

  const onDelete = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await remove(pendingDelete.entry_id);
      toast("Report deleted", "success");
      setPendingDelete(null);
    } catch {
      toast("Could not delete the report", "error");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="card-container overflow-hidden">
      <div className="px-4 pt-3 pb-1 flex items-center gap-2">
        <FileText size={13} className="text-text-muted" />
        <h2 className="text-xs font-semibold text-text-primary">Generated reports</h2>
        <span className="text-[11px] text-text-muted">Stored in the application</span>
      </div>
      {library.isLoading ? (
        <div className="p-5 space-y-2">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="h-9 bg-nav-hover rounded animate-pulse" />
          ))}
        </div>
      ) : reports.length === 0 ? (
        <p className="px-4 pb-4 text-xs text-text-muted">
          No reports yet. Completed reports appear here with download and delete options.
        </p>
      ) : (
        <ul className="px-4 pb-3 space-y-1.5">
          {reports.map((r) => (
            <li
              key={r.entry_id}
              className="flex items-center gap-2 p-2 rounded-btn border border-border hover:bg-nav-hover transition-colors"
            >
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-text-primary truncate" title={r.filename}>
                  {r.filename}
                </p>
                <p className="text-[11px] text-text-muted truncate">
                  {fmtCreatedAt(r.created_at)}
                  {r.topics.length > 0 ? ` · ${r.topics.join(" · ")}` : ""}
                </p>
              </div>
              <a
                href={r.download_url}
                download
                title="Download Word document"
                aria-label={`Download ${r.filename}`}
                className="p-2 rounded-btn text-text-muted hover:text-accent hover:bg-nav-hover transition-colors"
              >
                <Download size={14} />
              </a>
              <button
                onClick={() => setPendingDelete({ entry_id: r.entry_id, label: r.filename })}
                title="Delete this report"
                aria-label={`Delete ${r.filename}`}
                className="p-2 rounded-btn text-text-muted hover:text-danger hover:bg-nav-hover transition-colors"
              >
                <Trash2 size={14} />
              </button>
            </li>
          ))}
        </ul>
      )}
      {pendingDelete ? (
        <ConfirmCard
          title="Delete report?"
          message={`"${pendingDelete.label}" and its charts will be removed. This cannot be undone.`}
          busy={deleting}
          onConfirm={() => { void onDelete(); }}
          onCancel={() => { if (!deleting) setPendingDelete(null); }}
        />
      ) : null}
    </div>
  );
}
