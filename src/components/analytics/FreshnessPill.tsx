import { useQueryClient } from "@tanstack/react-query";
import { Database, RefreshCw } from "lucide-react";
import { useAnalyticsFreshness, useAnalyticsRefresh } from "@/hooks/useAnalytics";
import { fmtDateShort } from "@/lib/format";

interface FreshnessPillProps {
  filters: Record<string, string[]>;
}

const DAY = 86_400_000;

/** "Data thru …" pill + fact-table rebuild button. */
export default function FreshnessPill({ filters }: FreshnessPillProps) {
  const { data } = useAnalyticsFreshness(filters);
  const refresh = useAnalyticsRefresh();
  const qc = useQueryClient();

  const factEnd = data?.fact_end ? new Date(`${data.fact_end}T00:00:00`).getTime() : null;
  const ageDays = factEnd ? Math.floor((Date.now() - factEnd) / DAY) : null;
  const tone = data == null
    ? "text-text-muted bg-nav-hover"
    : data.fact_is_empty
      ? "bg-badge-red-bg text-badge-red-text"
      : ageDays == null || ageDays > 7
        ? "bg-badge-amber-bg text-badge-amber-text"
        : "bg-badge-green-bg text-badge-green-text";
  const dot = data == null
    ? "bg-text-muted"
    : data.fact_is_empty ? "bg-danger" : ageDays == null || ageDays > 7 ? "bg-warning" : "bg-success";

  const lastIngest = data?.last_ingest;
  const titleLines = [
    data?.fact_is_empty
      ? "Analytics table not built yet — click Refresh to build it"
      : `Analytics data covers ${data?.fact_start || "—"} → ${data?.fact_end || "—"}`,
    lastIngest
      ? `Last upload: ${lastIngest.filename} (${lastIngest.report_type}, ${lastIngest.status})`
      : "No uploads recorded",
    data?.quarantine_rows ? `${data.quarantine_rows} quarantined row(s) awaiting review` : "Quarantine empty",
  ];

  const handleRefresh = async () => {
    await refresh.mutateAsync();
    qc.invalidateQueries({ queryKey: ["analytics-"] });
  };

  return (
    <div className="flex items-center gap-1.5">
      <div
        className={`hidden md:flex items-center gap-1.5 px-2.5 py-1.5 rounded-btn text-[11px] font-medium ${tone}`}
        title={titleLines.join("\n")}
      >
        <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
        <Database size={11} />
        {data == null
          ? "Data status…"
          : data.fact_is_empty
            ? "No analytics data"
            : `Data thru ${fmtDateShort(data.fact_end)}`}
      </div>
      <button
        onClick={handleRefresh}
        disabled={refresh.isPending}
        className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs border border-border rounded-btn text-text-secondary hover:bg-nav-hover disabled:opacity-50 transition-colors"
        title="Rebuild the analytics fact table with current rules"
      >
        <RefreshCw size={12} className={refresh.isPending ? "animate-spin" : ""} />
        <span className="hidden lg:inline">Refresh</span>
      </button>
    </div>
  );
}
