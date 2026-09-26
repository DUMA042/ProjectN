import { STATUS_COLORS, STATUS_LABELS } from "@/lib/analyticsColors";
import { fmtNum } from "@/lib/format";

export interface StackedRow {
  label: string;
  parts: { key: string; value: number }[];
  onClick?: () => void;
}

interface StackedStatusBarsProps {
  rows: StackedRow[];
  loading?: boolean;
}

/** 100% horizontal bars of day-status mix — one bar per group/period. */
export default function StackedStatusBars({ rows, loading }: StackedStatusBarsProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-8 bg-nav-hover rounded animate-pulse" />
        ))}
      </div>
    );
  }
  const keys = Array.from(new Set(rows.flatMap((r) => r.parts.map((p) => p.key))));
  const legend = keys.filter((k) => STATUS_COLORS[k]);

  return (
    <div>
      <div className="space-y-2">
        {rows.map((r) => {
          const total = r.parts.reduce((s, p) => s + p.value, 0) || 1;
          return (
            <button
              key={r.label}
              onClick={r.onClick}
              className={`w-full text-left group ${r.onClick ? "cursor-pointer" : "cursor-default"}`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-text-secondary truncate group-hover:text-text-primary transition-colors">
                  {r.label}
                </span>
                <span className="text-[11px] text-text-muted tabular-nums flex-shrink-0 ml-2">{fmtNum(total)} days</span>
              </div>
              <div className="flex w-full h-4 rounded-[4px] overflow-hidden bg-[#F1F5F9]">
                {r.parts.map((p) => (
                  <span
                    key={p.key}
                    title={`${STATUS_LABELS[p.key] || p.key}: ${p.value}`}
                    style={{ width: `${(p.value / total) * 100}%`, backgroundColor: STATUS_COLORS[p.key] || "#CBD5E1" }}
                    className="h-full transition-all duration-500"
                  />
                ))}
              </div>
            </button>
          );
        })}
        {rows.length === 0 && <p className="text-xs text-text-muted text-center py-6">No data</p>}
      </div>
      {legend.length > 0 && (
        <div className="flex items-center gap-3 flex-wrap mt-3 pt-2 border-t border-divider">
          {legend.map((k) => (
            <span key={k} className="flex items-center gap-1 text-[11px] text-text-secondary">
              <span className="w-2 h-2 rounded-[2px]" style={{ backgroundColor: STATUS_COLORS[k] }} />
              {STATUS_LABELS[k] || k}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
