import { FileWarning, UploadCloud, ShieldCheck } from "lucide-react";
import BulletMeter from "./BulletMeter";
import type { Freshness } from "@/hooks/useAnalytics";
import { fmtDateShort, fmtNum } from "@/lib/format";

interface DataHealthCardProps {
  health: Freshness | undefined;
  loading: boolean;
}

/** How trustworthy is what you're looking at? Fact span, coverage, ingest, quarantine. */
export default function DataHealthCard({ health, loading }: DataHealthCardProps) {
  return (
    <div className="card-container p-4">
      <div className="flex items-center gap-2 mb-3">
        <ShieldCheck size={14} className="text-accent" />
        <h4 className="text-xs font-semibold text-text-primary">Data Health</h4>
      </div>

      {loading || !health ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-8 bg-nav-hover rounded animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="space-y-3.5">
          <BulletMeter
            label="Swipe coverage"
            value={health.coverage ?? 0}
            max={100}
            unit="%"
            dangerBelow={50}
          />
          <div className="flex items-center justify-between text-[11px]">
            <span className="flex items-center gap-1.5 text-text-muted">
              <UploadCloud size={12} />
              Fact table
            </span>
            <span className="text-text-secondary font-medium">
              {health.fact_is_empty
                ? "not built"
                : `${fmtDateShort(health.fact_start)} → ${fmtDateShort(health.fact_end)} · ${fmtNum(health.fact_rows)} rows`}
            </span>
          </div>
          <div className="flex items-center justify-between text-[11px]">
            <span className="flex items-center gap-1.5 text-text-muted">
              <UploadCloud size={12} />
              Last upload
            </span>
            <span className="text-text-secondary font-medium max-w-[55%] truncate" title={health.last_ingest?.filename || ""}>
              {health.last_ingest
                ? `${health.last_ingest.report_type} · ${fmtDateShort(health.last_ingest.created_at)}`
                : "none recorded"}
            </span>
          </div>
          <div className="flex items-center justify-between text-[11px]">
            <span className="flex items-center gap-1.5 text-text-muted">
              <FileWarning size={12} className={health.quarantine_rows > 0 ? "text-warning" : ""} />
              Quarantine
            </span>
            <span className={`font-medium ${health.quarantine_rows > 0 ? "text-warning" : "text-text-secondary"}`}>
              {health.quarantine_rows > 0 ? `${fmtNum(health.quarantine_rows)} row(s) to review` : "clear"}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
