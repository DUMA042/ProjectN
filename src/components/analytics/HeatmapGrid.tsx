import { useMemo } from "react";
import { ChevronDown } from "lucide-react";

interface DimOption {
  key: string;
  label: string;
}

interface HeatmapGridProps {
  title: string;
  rowDim: string;
  colDim: string;
  dimOptions: DimOption[];
  onRowDimChange: (key: string) => void;
  onColDimChange: (key: string) => void;
  rowValues: string[];
  colValues: string[];
  value: (row: string, col: string) => number | null;
  onCellClick?: (row: string, col: string) => void;
  suffix?: string;
  loading?: boolean;
}

function colorFor(v: number, min: number, max: number): string {
  if (max <= min) return "rgba(22,119,255,0.25)";
  const t = (v - min) / (max - min);
  // light blue -> strong blue
  return `rgba(22,119,255,${0.12 + t * 0.78})`;
}

export default function HeatmapGrid({
  title, rowDim, colDim, dimOptions, onRowDimChange, onColDimChange,
  rowValues, colValues, value, onCellClick, suffix = "", loading,
}: HeatmapGridProps) {
  const { min, max } = useMemo(() => {
    let mn = Infinity, mx = -Infinity;
    for (const r of rowValues) for (const c of colValues) {
      const v = value(r, c);
      if (v != null && Number.isFinite(v)) { mn = Math.min(mn, v); mx = Math.max(mx, v); }
    }
    if (mn === Infinity) { mn = 0; mx = 1; }
    return { min: mn, max: mx };
  }, [rowValues, colValues, value]);

  const Select = ({ value: v, onChange }: { value: string; onChange: (k: string) => void }) => (
    <div className="relative">
      <select
        value={v}
        onChange={(e) => onChange(e.target.value)}
        className="appearance-none pl-2 pr-6 py-1 text-[11px] border border-border rounded-btn bg-surface text-text-secondary cursor-pointer hover:bg-nav-hover"
      >
        {dimOptions.map((d) => (
          <option key={d.key} value={d.key}>{d.label}</option>
        ))}
      </select>
      <ChevronDown size={12} className="absolute right-1.5 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" />
    </div>
  );

  return (
    <div className="card-container p-4">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h4 className="text-xs font-semibold text-text-primary">{title}</h4>
        <div className="flex items-center gap-1.5 text-[11px] text-text-muted">
          <Select value={rowDim} onChange={onRowDimChange} />
          <span>×</span>
          <Select value={colDim} onChange={onColDimChange} />
        </div>
      </div>
      {loading ? (
        <div className="h-[240px] bg-nav-hover rounded animate-pulse" />
      ) : rowValues.length === 0 || colValues.length === 0 ? (
        <p className="text-xs text-text-muted text-center py-16">No data</p>
      ) : (
        <div className="overflow-auto max-h-[320px]">
          <table className="border-separate border-spacing-0.5 text-[10px]">
            <thead>
              <tr>
                <th className="sticky left-0 bg-surface z-10" />
                {colValues.map((c) => (
                  <th key={c} className="px-1 py-1 font-medium text-text-muted whitespace-nowrap text-center">{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rowValues.map((r) => (
                <tr key={r}>
                  <td className="sticky left-0 bg-surface z-10 pr-2 text-right font-medium text-text-secondary whitespace-nowrap">{r}</td>
                  {colValues.map((c) => {
                    const v = value(r, c);
                    return (
                      <td
                        key={c}
                        title={`${r} · ${c}: ${v == null ? "—" : `${v}${suffix}`}`}
                        onClick={() => v != null && onCellClick?.(r, c)}
                        className={`w-9 h-7 rounded-[3px] text-center align-middle ${onCellClick && v != null ? "cursor-pointer" : ""}`}
                        style={{ backgroundColor: v == null ? "#F5F5F5" : colorFor(v, min, max), color: v != null && v > (min + max) / 2 ? "#fff" : "#0F172A" }}
                      >
                        {v == null ? "" : v}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
