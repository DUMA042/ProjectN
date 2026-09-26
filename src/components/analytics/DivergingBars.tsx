import { fmtDelta } from "@/lib/format";
import { SUCCESS, DANGER } from "@/lib/analyticsColors";

export interface DivergingRow {
  label: string;
  value: number;
  sub?: string;
  onClick?: () => void;
}

interface DivergingBarsProps {
  rows: DivergingRow[];
  /** Suffix for the value (e.g. "pp" for percentage points). */
  unit?: string;
  loading?: boolean;
  /** Explicit max |value| for the axis scale. */
  maxAbs?: number;
}

/** Center-axis delta bars — improvements grow right (green), declines left (red). */
export default function DivergingBars({ rows, unit = "", loading, maxAbs }: DivergingBarsProps) {
  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-6 bg-nav-hover rounded animate-pulse" />
        ))}
      </div>
    );
  }
  if (rows.length === 0) {
    return <p className="text-xs text-text-muted text-center py-6">No change vs previous period</p>;
  }
  const max = maxAbs ?? Math.max(...rows.map((r) => Math.abs(r.value)), 1);

  return (
    <div className="space-y-1">
      {rows.map((r) => {
        const pct = (Math.abs(r.value) / max) * 50;
        const positive = r.value >= 0;
        return (
          <button
            key={r.label}
            onClick={r.onClick}
            className={`w-full flex items-center gap-2 px-1.5 py-1 rounded-btn ${r.onClick ? "hover:bg-nav-hover cursor-pointer" : "cursor-default"}`}
          >
            <span className="w-28 text-xs text-text-secondary truncate text-right flex-shrink-0" title={r.label}>
              {r.label}
            </span>
            <span className="relative flex-1 h-4 bg-[#FAFAFA] rounded-[3px] overflow-hidden">
              {/* center axis */}
              <span className="absolute inset-y-0 left-1/2 w-px bg-border" />
              <span
                className="absolute inset-y-[3px] rounded-[2px]"
                style={{
                  backgroundColor: positive ? SUCCESS : DANGER,
                  width: `${pct}%`,
                  left: positive ? "50%" : `${50 - pct}%`,
                  transition: "width 0.6s cubic-bezier(0.22, 1, 0.36, 1)",
                }}
              />
            </span>
            <span
              className={`w-16 text-xs font-semibold tabular-nums flex-shrink-0 ${positive ? "text-badge-green-text" : "text-badge-red-text"}`}
            >
              {fmtDelta(r.value, unit)}
            </span>
          </button>
        );
      })}
    </div>
  );
}
