import { useMemo, useState } from "react";
import StaggerReveal, { RevealItem } from "@/components/analytics/StaggerReveal";
import TrendChart from "@/components/analytics/TrendChart";
import type { TrendPoint } from "@/components/analytics/TrendChart";
import HeatmapGrid from "@/components/analytics/HeatmapGrid";
import DivergingBars from "@/components/analytics/DivergingBars";
import CompositionChart from "@/components/analytics/CompositionChart";
import MetricPicker from "@/components/analytics/MetricPicker";
import { useAnalyticsExplore, useAnalyticsDimensions, useAnalyticsMetrics, type MetricMeta } from "@/hooks/useAnalytics";
import { makeSemanticScale, readableFg } from "@/lib/analyticsColors";
import { buildHeatOptions } from "@/lib/heatmapPairs";
import { useTabExport } from "./exportRegistry";
import { exportToCSV } from "@/lib/csvExport";
import { fmtDateShort } from "@/lib/format";

interface TrendsTabProps {
  filters: Record<string, string[]>;
  dateRange: { start: string; end: string } | null;
  compare: boolean;
  onDrill: (dimension: string, value: string) => void;
}

const GRANS = [
  { key: "day", label: "Day" },
  { key: "week", label: "Week" },
  { key: "month", label: "Month" },
  { key: "quarter", label: "Quarter" },
];

const DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function isoDay(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function periodLabel(v: string, gran: string): string {
  if (!v) return "—";
  const d = new Date(v.length === 10 ? `${v}T00:00:00` : v);
  if (isNaN(d.getTime())) return String(v);
  if (gran === "month") return d.toLocaleDateString("en-GB", { month: "short", year: "numeric" });
  if (gran === "quarter") {
    const q = Math.floor(d.getMonth() / 3) + 1;
    return `Q${q} ${d.getFullYear()}`;
  }
  return fmtDateShort(v);
}

function prevRange(dr: { start: string; end: string } | null) {
  if (!dr) return null;
  const s = new Date(`${dr.start}T00:00:00`);
  const e = new Date(`${dr.end}T00:00:00`);
  const len = Math.round((e.getTime() - s.getTime()) / 86_400_000) + 1;
  const pe = new Date(s); pe.setDate(s.getDate() - 1);
  const ps = new Date(pe); ps.setDate(pe.getDate() - (len - 1));
  return { start: isoDay(ps), end: isoDay(pe) };
}

export default function TrendsTab({ filters, dateRange, compare, onDrill }: TrendsTabProps) {
  const [metricKey, setMetricKey] = useState("attendance_rate");
  const [gran, setGran] = useState("week");
  const [heatRow, setHeatRow] = useState("department");
  const [heatCol, setHeatCol] = useState("month");
  const [deltaDim, setDeltaDim] = useState("department");

  const { data: metricData } = useAnalyticsMetrics();
  const { data: dims } = useAnalyticsDimensions();
  const metric: MetricMeta | undefined = useMemo(
    () => (metricData?.metrics || []).find((m) => m.key === metricKey),
    [metricData, metricKey]
  );
  const heatOpts = useMemo(
    () => buildHeatOptions((dims?.dimensions || []).map((d) => ({ key: d.key, label: d.label }))),
    [dims]
  );
  const domain = metric?.domain || "attendance";
  const isRate = metric?.type === "pct";
  const suffix = isRate ? "%" : "";
  const isTimeless = domain === "employees";

  const dimOptions = (dims?.dimensions || [])
    .filter((d) => d.kind === "attribute")
    .map((d) => ({ key: d.key, label: d.label }));

  // ── Trend (current + previous) ────────────────────────────────────────────
  const trend = useAnalyticsExplore({
    domain, group_by: [gran], metrics: [metricKey],
    filters, date_range: dateRange, sort_by: gran, sort_dir: "asc", page_size: 400,
  });
  const prevDr = useMemo(() => prevRange(dateRange), [dateRange]);
  const trendPrevQ = useAnalyticsExplore({
    domain, group_by: [gran], metrics: [metricKey],
    filters, date_range: prevDr, sort_by: gran, sort_dir: "asc", page_size: 400,
    enabled: compare && !!prevDr && !isTimeless,
  });

  const toPoints = (rows: Record<string, unknown>[]): TrendPoint[] =>
    rows.map((g) => ({ label: periodLabel(String(g[gran] ?? ""), gran), value: Number(g[metricKey] ?? 0) }));

  const trendData: TrendPoint[] = useMemo(
    () => toPoints(trend.data?.groups || []),
    [trend.data, gran, metricKey] // eslint-disable-line react-hooks/exhaustive-deps
  );
  const trendPrev: TrendPoint[] | undefined = compare
    ? toPoints(trendPrevQ.data?.groups || [])
    : undefined;

  // ── Day-grain series for seasonality patterns ─────────────────────────────
  const daily = useAnalyticsExplore({
    domain, group_by: ["day"], metrics: [metricKey],
    filters, date_range: dateRange, sort_by: "day", sort_dir: "asc", page_size: 500,
    enabled: !isTimeless,
  });
  const dowData = useMemo(() => {
    const buckets = new Map<number, { sum: number; n: number }>();
    (daily.data?.groups || []).forEach((g: Record<string, unknown>) => {
      const d = new Date(`${String(g.day)}T00:00:00`);
      if (isNaN(d.getTime())) return;
      const dow = (d.getDay() + 6) % 7;
      const b = buckets.get(dow) || { sum: 0, n: 0 };
      b.sum += Number(g[metricKey] ?? 0);
      b.n += 1;
      buckets.set(dow, b);
    });
    return DOW.map((name, i) => ({ name, value: buckets.has(i) ? Math.round(((buckets.get(i)!.sum) / buckets.get(i)!.n) * 10) / 10 : 0 }))
      .filter((r) => r.value !== 0);
  }, [daily.data, metricKey]);

  const monthData = useMemo(() => {
    const buckets = new Map<string, { sum: number; n: number }>();
    (daily.data?.groups || []).forEach((g: Record<string, unknown>) => {
      const m = String(g.day || "").slice(0, 7);
      if (!m) return;
      const b = buckets.get(m) || { sum: 0, n: 0 };
      b.sum += Number(g[metricKey] ?? 0);
      b.n += 1;
      buckets.set(m, b);
    });
    return [...buckets.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([m, b]) => ({
        name: new Date(`${m}-01T00:00:00`).toLocaleDateString("en-GB", { month: "short", year: "2-digit" }),
        value: Math.round((b.sum / b.n) * 10) / 10,
      }));
  }, [daily.data, metricKey]);

  // ── Heatmap (row dim × time bucket) ───────────────────────────────────────
  const heat = useAnalyticsExplore({
    domain, group_by: [heatRow, heatCol], metrics: [metricKey],
    filters, date_range: dateRange, page_size: 2000,
    enabled: !isTimeless,
  });
  const heatGroups: Record<string, unknown>[] = heat.data?.groups || [];
  const rowValues = useMemo(
    () => Array.from(new Set(heatGroups.map((g) => periodLabel(String(g[heatRow] ?? ""), heatRow === "department" ? "raw" : "raw")))),
    [heatGroups, heatRow]
  );
  const colValues = useMemo(
    () => Array.from(new Set(heatGroups.map((g) => periodLabel(String(g[heatCol] ?? ""), heatCol)))),
    [heatGroups, heatCol]
  );
  const heatMap = useMemo(() => {
    const m = new Map<string, number>();
    heatGroups.forEach((g) => {
      m.set(
        `${periodLabel(String(g[heatRow] ?? ""), "raw")}|${periodLabel(String(g[heatCol] ?? ""), heatCol)}`,
        Number(g[metricKey] ?? 0)
      );
    });
    return m;
  }, [heatGroups, heatRow, heatCol, metricKey]);
  const heatCellColor = useMemo(() => {
    if (!metric) return undefined;
    const scale = makeSemanticScale(metric, [...heatMap.values()]);
    return (v: number) => {
      const bg = scale(v);
      return { bg, fg: readableFg(bg) };
    };
  }, [metric, heatMap]);

  // ── Δ vs previous by segment ──────────────────────────────────────────────
  const curByDim = useAnalyticsExplore({
    domain, group_by: [deltaDim], metrics: [metricKey],
    filters, date_range: dateRange, page_size: 100, sort_by: metricKey, sort_dir: "desc",
  });
  const prevByDim = useAnalyticsExplore({
    domain, group_by: [deltaDim], metrics: [metricKey],
    filters, date_range: prevDr, page_size: 100, sort_by: metricKey, sort_dir: "desc",
    enabled: compare && !!prevDr && !isTimeless,
  });
  const deltaRows = useMemo(() => {
    if (!compare) return [];
    const cur = new Map<string, number>();
    (curByDim.data?.groups || []).forEach((g: Record<string, unknown>) => {
      const k = String(g[deltaDim] ?? "—");
      if (g[metricKey] != null) cur.set(k, Number(g[metricKey]));
    });
    const prev = new Map<string, number>();
    (prevByDim.data?.groups || []).forEach((g: Record<string, unknown>) => {
      const k = String(g[deltaDim] ?? "—");
      if (g[metricKey] != null) prev.set(k, Number(g[metricKey]));
    });
    const rows: { label: string; value: number; onClick?: () => void }[] = [];
    cur.forEach((c, k) => {
      const p = prev.get(k);
      if (p == null) return;
      rows.push({ label: k, value: Math.round((c - p) * 10) / 10, onClick: () => onDrill(deltaDim, k) });
    });
    rows.sort((a, b) => b.value - a.value);
    return rows;
  }, [compare, curByDim.data, prevByDim.data, deltaDim, metricKey]); // eslint-disable-line react-hooks/exhaustive-deps

  const dimLabel = (key: string) => dims?.dimensions.find((d) => d.key === key)?.label || key;

  useTabExport(
    deltaRows.length > 0 || trendData.length > 0
      ? () => {
          const rows = [
            ...trendData.map((p) => ({ series: metric?.label || metricKey, period: p.label, value: p.value })),
            ...deltaRows.map((r) => ({ series: `Δ ${metric?.label || metricKey} vs previous`, period: r.label, value: r.value })),
          ];
          exportToCSV(rows, `trends_${metricKey}`, dateRange ? { startDate: dateRange.start, endDate: dateRange.end } : undefined);
        }
      : null
  );

  return (
    <StaggerReveal className="space-y-4">
      {/* Trend card with metric + granularity pickers */}
      <RevealItem>
        <div className="card-container p-4">
          <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
            <h4 className="text-xs font-semibold text-text-primary">
              {metric?.label || "Metric"} over time
            </h4>
            <div className="flex items-center gap-2">
              <MetricPicker
                value={metricKey}
                onChange={(k) => setMetricKey(Array.isArray(k) ? (k[0] || "attendance_rate") : k)}
                label="Metric"
              />
              <div className="flex items-center gap-0.5 bg-nav-hover rounded-btn p-0.5">
                {GRANS.map((g) => (
                  <button
                    key={g.key}
                    onClick={() => setGran(g.key)}
                    className={`px-2.5 py-1 text-xs font-medium rounded-[5px] transition-all ${
                      gran === g.key ? "bg-surface text-accent shadow-sm" : "text-text-secondary hover:text-text-primary"
                    }`}
                  >
                    {g.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
          {isTimeless ? (
            <p className="text-xs text-text-muted text-center py-12">
              Workforce metrics don't vary over time — pick an Attendance, Leave or Training metric above,
              or use Explore for workforce composition.
            </p>
          ) : (
            <TrendChart data={trendData} compareData={trendPrev} suffix={suffix} loading={trend.isLoading} height={240} />
          )}
        </div>
      </RevealItem>

      {/* Workforce subject: composition instead of time cards */}
      {isTimeless ? (
        <RevealItem>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <CompositionExplorer metricKey={metricKey} filters={filters} onDrill={onDrill} />
            <div className="card-container p-4">
              <h4 className="text-xs font-semibold text-text-primary mb-3">Tip</h4>
              <p className="text-xs text-text-secondary leading-relaxed">
                Headcount and Active are snapshot metrics. To see how attendance, leave or training
                trend over time, switch the metric above to any non-Workforce subject — the whole tab
                re-runs on that data.
              </p>
            </div>
          </div>
        </RevealItem>
      ) : (
        <>
          <RevealItem>
            <HeatmapGrid
              title={`${metric?.label || "Metric"} — ${dimLabel(heatRow)} × ${dimLabel(heatCol)}`}
              rowDim={heatRow} colDim={heatCol}
              dimOptions={heatOpts.rowOptions}
              colDimOptions={heatOpts.colOptionsFor(heatRow)}
              onRowDimChange={(k) => {
                const g = heatOpts.guardRow(k, heatCol);
                setHeatRow(g.row);
                setHeatCol(g.col);
              }}
              onColDimChange={(k) => {
                const c = heatOpts.guardCol(k, heatRow);
                if (c != null) setHeatCol(c);
              }}
              rowValues={rowValues} colValues={colValues}
              value={(r, c) => heatMap.get(`${r}|${c}`) ?? null}
              suffix={suffix}
              loading={heat.isLoading}
              cellColor={heatCellColor}
            />
          </RevealItem>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <RevealItem>
              <div className="card-container p-4">
                <h4 className="text-xs font-semibold text-text-primary mb-3">By day of week</h4>
                <CompositionChart title="" data={dowData} loading={daily.isLoading} onSelect={(n) => {}} />
                <p className="text-[11px] text-text-muted mt-2">Average {metric?.label.toLowerCase()} per weekday</p>
              </div>
            </RevealItem>
            <RevealItem>
              <div className="card-container p-4">
                <h4 className="text-xs font-semibold text-text-primary mb-3">By month</h4>
                <CompositionChart title="" data={monthData} color="#722ED1" loading={daily.isLoading} onSelect={(n) => {}} />
                <p className="text-[11px] text-text-muted mt-2">Average {metric?.label.toLowerCase()} per month</p>
              </div>
            </RevealItem>
            <RevealItem>
              <div className="card-container p-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-xs font-semibold text-text-primary">Δ vs previous</h4>
                  <select
                    value={deltaDim}
                    onChange={(e) => setDeltaDim(e.target.value)}
                    className="px-2 py-1 text-[11px] border border-border rounded-btn bg-surface text-text-secondary cursor-pointer"
                  >
                    {dimOptions.map((d) => <option key={d.key} value={d.key}>{d.label}</option>)}
                  </select>
                </div>
                {compare ? (
                  <DivergingBars rows={deltaRows} unit={isRate ? "pp" : ""} loading={curByDim.isLoading || prevByDim.isFetching} />
                ) : (
                  <p className="text-xs text-text-muted text-center py-8">Enable “Compare previous” to see deltas.</p>
                )}
              </div>
            </RevealItem>
          </div>
        </>
      )}
    </StaggerReveal>
  );
}

/** Workforce composition fallback for the timeless employees subject. */
function CompositionExplorer({
  metricKey, filters, onDrill,
}: {
  metricKey: string;
  filters: Record<string, string[]>;
  onDrill: (dimension: string, value: string) => void;
}) {
  const [dim, setDim] = useState("department");
  const { data: dims } = useAnalyticsDimensions();
  const q = useAnalyticsExplore({
    domain: "employees", group_by: [dim], metrics: [metricKey],
    filters, page_size: 100, sort_by: metricKey, sort_dir: "desc",
  });
  const data = (q.data?.groups || []).map((g: Record<string, unknown>) => ({
    name: String(g[dim] ?? "—"), value: Number(g[metricKey] ?? 0),
  }));
  return (
    <div className="card-container p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-semibold text-text-primary">Workforce composition</h4>
        <select
          value={dim}
          onChange={(e) => setDim(e.target.value)}
          className="px-2 py-1 text-[11px] border border-border rounded-btn bg-surface text-text-secondary cursor-pointer"
        >
          {(dims?.dimensions || []).filter((d) => d.kind === "attribute").map((d) => (
            <option key={d.key} value={d.key}>{d.label}</option>
          ))}
        </select>
      </div>
      <CompositionChart title="" data={data} loading={q.isLoading} onSelect={(n) => onDrill(dim, n)} />
    </div>
  );
}
