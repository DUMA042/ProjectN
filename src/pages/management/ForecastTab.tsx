import { useMemo } from "react";
import { Info } from "lucide-react";
import StaggerReveal, { RevealItem } from "@/components/analytics/StaggerReveal";
import TrendChart from "@/components/analytics/TrendChart";
import type { TrendPoint, BandPoint } from "@/components/analytics/TrendChart";
import { useAnalyticsForecast, type ForecastWeek } from "@/hooks/useAnalytics";
import { semanticColor, readableFg } from "@/lib/analyticsColors";
import { fmtDateShort, fmtNum } from "@/lib/format";
import { useTabExport } from "./exportRegistry";
import { exportToCSV } from "@/lib/csvExport";

interface ForecastTabProps {
  filters: Record<string, string[]>;
  onOpenEmployee: (id: string) => void;
}

function splitSeries(series: ForecastWeek[] | undefined): {
  actual: TrendPoint[];
  projection: TrendPoint[];
  band: BandPoint[];
} {
  const actual: TrendPoint[] = [];
  const projection: TrendPoint[] = [];
  const band: BandPoint[] = [];
  (series || []).forEach((p) => {
    if (p.actual) actual.push({ label: fmtDateShort(p.label), value: p.value });
    else {
      projection.push({ label: fmtDateShort(p.label), value: p.value });
      if (p.bandLow != null && p.bandHigh != null) band.push({ label: fmtDateShort(p.label), low: p.bandLow, high: p.bandHigh });
    }
  });
  return { actual, projection, band };
}

/** Coverage cells read good/bad without numbers: blue above 60% of headcount
 * available, red below — same semantic scale as the rest of the workspace. */
function ratioColor(available: number, headcount: number): { bg: string; fg: string } {
  const pct = headcount > 0 ? (available / headcount) * 100 : 0;
  const bg = semanticColor(pct, { polarity: "up_good", pivot: 60 }, 60, 40);
  return { bg, fg: readableFg(bg) };
}

export default function ForecastTab({ filters, onOpenEmployee }: ForecastTabProps) {
  const { data, isLoading } = useAnalyticsForecast(filters);

  const att = useMemo(() => splitSeries(data?.projection), [data]);
  const leave = useMemo(() => splitSeries(data?.leave_forecast), [data]);

  useTabExport(
    data
      ? () => {
          const coverageRows: Record<string, unknown>[] = (data.coverage.departments || []).map((d) => {
            const row: Record<string, unknown> = { department: d.department, headcount: d.headcount };
            (d.weeks || []).forEach((w, i) => {
              row[`week_${i + 1} (${fmtDateShort(w.week)})`] = `${w.available} of ${w.headcount} (leave ${w.expected_leave}, training ${w.scheduled_training})`;
            });
            return row;
          });
          exportToCSV(
            [
              ...coverageRows,
              {},
              ...data.risks.map((r) => ({
                employee: r.full_name, department: r.department,
                absent_30d: r.recent_absent, late_30d: r.recent_late,
                baseline_per_30d: r.baseline_per_30d, ratio: r.ratio,
              })),
            ],
            "forecast",
            undefined
          );
        }
      : null
  );

  const coverageWeeks = data?.coverage.weeks || [];

  return (
    <StaggerReveal className="space-y-4">
      {/* Projections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <RevealItem>
          <div className="card-container p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-semibold text-text-primary">Projected attendance rate</h4>
              <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-badge-blue-bg text-badge-blue-text">
                projection
              </span>
            </div>
            {isLoading ? (
              <div className="h-[240px] bg-nav-hover rounded animate-pulse" />
            ) : att.actual.length === 0 ? (
              <p className="text-xs text-text-muted text-center py-16">Not enough weekly history to project.</p>
            ) : (
              <>
                <TrendChart data={att.actual} projectionData={att.projection} bandData={att.band} suffix="%" height={240} loading={false} />
                <p className="flex items-start gap-1.5 text-[11px] text-text-muted mt-3 pt-2 border-t border-divider">
                  <Info size={12} className="mt-0.5 flex-shrink-0" />
                  {data?.method}
                </p>
              </>
            )}
          </div>
        </RevealItem>

        <RevealItem>
          <div className="card-container p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-semibold text-text-primary">Staff on leave · weekly</h4>
              <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-badge-blue-bg text-badge-blue-text">
                projection
              </span>
            </div>
            {isLoading ? (
              <div className="h-[240px] bg-nav-hover rounded animate-pulse" />
            ) : leave.actual.length === 0 ? (
              <p className="text-xs text-text-muted text-center py-16">Not enough weekly history to project.</p>
            ) : (
              <TrendChart data={leave.actual} projectionData={leave.projection} bandData={leave.band} height={240} loading={false} />
            )}
          </div>
        </RevealItem>
      </div>

      {/* Coverage outlook */}
      <RevealItem>
        <div className="card-container p-4">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <h4 className="text-xs font-semibold text-text-primary">Coverage outlook · next {coverageWeeks.length} weeks</h4>
            <p className="text-[11px] text-text-muted">Available = active − expected leave − scheduled training</p>
          </div>
          {isLoading ? (
            <div className="h-32 bg-nav-hover rounded animate-pulse" />
          ) : (data?.coverage.departments || []).length === 0 ? (
            <p className="text-xs text-text-muted text-center py-10">No departments in scope.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left">
                    <th className="py-1.5 pr-3 font-medium text-text-secondary">Department</th>
                    {coverageWeeks.map((w) => (
                      <th key={w} className="py-1.5 px-2 font-medium text-text-secondary whitespace-nowrap">
                        W/C {fmtDateShort(w)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(data?.coverage.departments || []).map((d) => (
                    <tr key={d.department} className="border-t border-divider">
                      <td className="py-1.5 pr-3 text-text-primary font-medium max-w-[180px] truncate" title={d.department}>
                        {d.department}
                        <span className="text-text-muted font-normal"> · {d.headcount}</span>
                      </td>
                      {d.weeks.map((w) => {
                        const fill = ratioColor(w.available, w.headcount);
                        return (
                          <td
                            key={w.week}
                            className="py-1.5 px-2 text-center"
                            title={`${w.available} available · ${w.expected_leave} expected leave · ${w.scheduled_training} in training`}
                          >
                            <span
                              className="inline-block min-w-[44px] px-1.5 py-1 rounded-[4px] font-semibold tabular-nums"
                              style={{ backgroundColor: fill.bg, color: fill.fg }}
                            >
                              {w.available}
                            </span>
                            {(w.expected_leave > 0 || w.scheduled_training > 0) && (
                              <span className="block text-[10px] text-text-muted">
                                −{Math.round(w.expected_leave + w.scheduled_training)}
                              </span>
                            )}
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
      </RevealItem>

      {/* Risk roster */}
      <RevealItem>
        <div className="card-container p-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-xs font-semibold text-text-primary">Risk roster</h4>
            <p className="text-[11px] text-text-muted">Trailing 30 days vs own 90-day baseline</p>
          </div>
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => <div key={i} className="h-8 bg-nav-hover rounded animate-pulse" />)}
            </div>
          ) : (data?.risks || []).length === 0 ? (
            <p className="text-xs text-text-muted text-center py-8">
              No one stands out — the trailing month looks like each person's own normal.
            </p>
          ) : (
            <div className="space-y-1">
              {data?.risks.map((r, i) => {
                const high = r.ratio != null && r.ratio >= 2;
                return (
                  <button
                    key={r.id_no}
                    onClick={() => onOpenEmployee(r.id_no)}
                    className="w-full flex items-center gap-2.5 px-2 py-2 rounded-btn hover:bg-nav-hover text-left transition-colors"
                  >
                    <span className="w-6 h-6 rounded-full bg-nav-hover text-[10px] font-bold text-text-secondary flex items-center justify-center flex-shrink-0">
                      {i + 1}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-xs font-medium text-text-primary truncate">{r.full_name}</span>
                      <span className="block text-[11px] text-text-muted truncate">{r.department}</span>
                    </span>
                    <span className="text-[11px] text-text-secondary tabular-nums whitespace-nowrap">
                      {fmtNum(r.recent_absent)} absent · {fmtNum(r.recent_late)} late
                    </span>
                    {r.ratio != null && (
                      <span
                        className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full whitespace-nowrap ${
                          high ? "bg-badge-red-bg text-badge-red-text" : "bg-nav-hover text-text-secondary"
                        }`}
                      >
                        {r.ratio}× baseline
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </RevealItem>
    </StaggerReveal>
  );
}
