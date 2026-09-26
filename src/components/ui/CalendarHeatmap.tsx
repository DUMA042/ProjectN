import { useMemo } from "react";
import { STATUS_COLORS, STATUS_LABELS } from "@/lib/analyticsColors";

export interface CalDay {
  /** ISO date */
  date: string;
  /** one of the STATUS_COLORS keys (lowercase) */
  status: string;
}

interface CalendarHeatmapProps {
  days: CalDay[];
  /** Cell size in px */
  cell?: number;
}

function isoDay(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** GitHub-style calendar heatmap of day statuses (drawer, 90-day view). */
export default function CalendarHeatmap({ days, cell = 13 }: CalendarHeatmapProps) {
  const statusByDate = useMemo(() => {
    const m = new Map<string, string>();
    days.forEach((d) => m.set(d.date.slice(0, 10), d.status.toLowerCase()));
    return m;
  }, [days]);

  const weeks = useMemo(() => {
    if (days.length === 0) return [];
    const sorted = [...days].map((d) => d.date.slice(0, 10)).sort();
    const start = new Date(`${sorted[0]}T00:00:00`);
    // align back to Monday
    const first = new Date(start);
    first.setDate(start.getDate() - ((start.getDay() + 6) % 7));
    const last = new Date(`${sorted[sorted.length - 1]}T00:00:00`);
    const cols: { date: string; status: string | undefined; inRange: boolean; monthLabel?: string }[][] = [];
    const cur = new Date(first);
    let colIdx = -1;
    while (cur <= last) {
      const dow = (cur.getDay() + 6) % 7; // 0=Mon
      if (dow === 0) {
        cols.push([]);
        colIdx += 1;
      }
      const dateStr = isoDay(cur);
      const monthStart = cur.getDate() <= 7 && dow === 0;
      cols[colIdx]?.push({
        date: dateStr,
        status: statusByDate.get(dateStr),
        inRange: statusByDate.has(dateStr),
        monthLabel: monthStart || colIdx === 0
          ? cur.toLocaleDateString("en-GB", { month: "short" })
          : undefined,
      });
      cur.setDate(cur.getDate() + 1);
    }
    return cols;
  }, [days, statusByDate]);

  const usedStatuses = useMemo(
    () => Array.from(new Set(days.map((d) => d.status.toLowerCase()))).filter((s) => STATUS_COLORS[s]),
    [days]
  );

  if (days.length === 0) {
    return <p className="text-xs text-text-muted text-center py-6">No day records in this period</p>;
  }

  return (
    <div className="overflow-x-auto">
      <div className="inline-flex flex-col gap-1">
        {/* month labels */}
        <div className="flex gap-[2px]" style={{ height: 14 }}>
          {weeks.map((col, i) => (
            <span key={i} className="text-[9px] text-text-muted whitespace-nowrap" style={{ width: cell }}>
              {col[0]?.monthLabel || ""}
            </span>
          ))}
        </div>
        {/* grid */}
        <div className="flex gap-[2px]">
          {weeks.map((col, i) => (
            <div key={i} className="flex flex-col gap-[2px]">
              {Array.from({ length: 7 }).map((_, row) => {
                const d = col[row];
                const status = d?.status;
                const color = status ? STATUS_COLORS[status] || "#E2E8F0" : "#F1F5F9";
                return (
                  <span
                    key={row}
                    title={d?.inRange ? `${d.date} — ${STATUS_LABELS[status || ""] || status || "no record"}` : d?.date}
                    className="rounded-[3px]"
                    style={{ width: cell, height: cell, backgroundColor: color }}
                  />
                );
              })}
            </div>
          ))}
        </div>
        {/* legend */}
        <div className="flex items-center gap-2.5 flex-wrap mt-1">
          {usedStatuses.map((s) => (
            <span key={s} className="flex items-center gap-1 text-[10px] text-text-secondary">
              <span className="w-2 h-2 rounded-[2px]" style={{ backgroundColor: STATUS_COLORS[s] }} />
              {STATUS_LABELS[s] || s}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
