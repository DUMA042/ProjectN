import { useIngestionDetails } from "@/hooks/useIngestion";

export default function DetailsContent({ ingestionId }: { ingestionId: string }) {
  const { data: details, isLoading } = useIngestionDetails(ingestionId);

  if (isLoading) {
    return (
      <div className="p-5 space-y-3 animate-pulse">
        <div className="grid grid-cols-3 gap-2">
          {[...Array(3)].map((_, i) => (<div key={i} className="h-16 bg-nav-hover rounded-card" />))}
        </div>
        {[...Array(5)].map((_, i) => (<div key={i} className="h-8 bg-nav-hover rounded-btn" />))}
      </div>
    );
  }

  if (!details) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-12 text-text-muted">
        <p className="text-sm">No details available</p>
      </div>
    );
  }

  const { summary, tables_breakdown, processor_report, failed_rows } = details;

  return (
    <>
      {/* Stat chips */}
      <div className="grid grid-cols-3 gap-2 px-5 pt-5">
        <div className="border border-border rounded-card p-3 text-center">
          <p className="text-lg font-bold text-success leading-6">
            {(summary.rows_loaded || 0).toLocaleString()}
          </p>
          <p className="text-[10px] text-text-muted uppercase">Rows Added</p>
        </div>
        <div className="border border-border rounded-card p-3 text-center">
          <p className={`text-lg font-bold leading-6 ${(summary.rows_failed || 0) > 0 ? "text-danger" : "text-text-secondary"}`}>
            {(summary.rows_failed || 0).toLocaleString()}
          </p>
          <p className="text-[10px] text-text-muted uppercase">Rows Failed</p>
        </div>
        <div className="border border-border rounded-card p-3 text-center">
          <p className={`text-lg font-bold leading-6 ${(summary.validation_rejected || 0) > 0 ? "text-warning" : "text-text-secondary"}`}>
            {(summary.validation_rejected || 0).toLocaleString()}
          </p>
          <p className="text-[10px] text-text-muted uppercase">Rejected</p>
        </div>
      </div>

      <div className="px-5 pt-4 space-y-1.5 text-xs">
        <div className="flex justify-between">
          <span className="text-text-muted">Uploaded</span>
          <span className="text-text-primary">{formatDate(details.created_at)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-muted">Processed</span>
          <span className="text-text-primary">{formatDate(details.processed_at)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-muted">Duration</span>
          <span className="text-text-primary">{formatDuration(details.duration_seconds)}</span>
        </div>
      </div>

      {tables_breakdown.length > 0 && (
        <div className="px-5 pt-4">
          <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">
            Database Tables Affected
          </p>
          <div className="border border-border rounded-card divide-y divide-divider">
            {tables_breakdown.map((t) => (
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

      {processor_report && (
        <div className="px-5 pt-4">
          <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">
            Processor Report
          </p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
            {([
              ["Rows read", processor_report.rows_read],
              ["New inserts", processor_report.new_inserts],
              ["Updates", processor_report.updates],
              ["Successes", processor_report.successes],
              ["Partial", processor_report.partial_successes],
              ["Failures", processor_report.failures],
            ] as [string, number | null | undefined][]).map(([label, value]) =>
              value != null ? (
                <div key={label} className="flex justify-between">
                  <span className="text-text-muted">{label}</span>
                  <span className="text-text-primary font-medium">{Number(value).toLocaleString()}</span>
                </div>
              ) : null
            )}
          </div>
        </div>
      )}

      {failed_rows.length > 0 && (
        <div className="px-5 pt-4 pb-5">
          <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">
            Failed Rows ({failed_rows.length})
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
                {failed_rows.slice(0, 50).map((r, i) => (
                  <tr key={i} className="border-b border-divider last:border-0">
                    <td className="px-3 py-1.5 text-text-secondary">{r.row}</td>
                    <td className="px-3 py-1.5 text-text-primary font-medium">{r.id_no}</td>
                    <td className="px-3 py-1.5 text-text-primary">{r.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {failed_rows.length > 50 && (
              <p className="px-3 py-2 text-[10px] text-text-muted">
                Showing first 50 of {failed_rows.length}
              </p>
            )}
          </div>
        </div>
      )}
    </>
  );
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-GB") + " " +
    new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}
