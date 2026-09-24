import { useMemo, useState } from "react";
import type { SortingState } from "@tanstack/react-table";
import KpiStrip from "@/components/analytics/KpiStrip";
import type { Kpi } from "@/components/analytics/KpiStrip";
import CompositionChart from "@/components/analytics/CompositionChart";
import TrendChart from "@/components/analytics/TrendChart";
import type { TrendPoint } from "@/components/analytics/TrendChart";
import HeatmapGrid from "@/components/analytics/HeatmapGrid";
import GroupByBar from "@/components/analytics/GroupByBar";
import DataTable from "@/components/ui/DataTable";
import { useAnalyticsDimensions, useAnalyticsExplore, useScopedTotals } from "@/hooks/useAnalytics";

interface AttendanceTabProps {
  filters: Record<string, string[]>;
  dateRange: { start: string; end: string } | null;
  compare: boolean;
  onDrill: (dimension: string, value: string) => void;
  onOpenEmployee: (id: string) => void;
}

const ATT_METRICS = [
  "attendance_rate", "absence_rate", "coverage", "present_days", "absent_days",
  "late_arrivals", "early_departures", "incomplete_days", "avg_work_minutes",
];

const TREND_GRANS = [
  { key: "day", label: "Day" },
  { key: "week", label: "Week" },
  { key: "month", label: "Month" },
];

const RANK_METRICS = [
  { key: "absent_days", label: "Absent Days" },
  { key: "late_arrivals", label: "Late Arrivals" },
  { key: "incomplete_days", label: "Incomplete Days" },
];

const RANK_COUNTS = [5, 10, 25, 50];

function fmtPeriod(v: string, gran: string): string {
  if (!v) return "—";
  const d = new Date(v + (v.length === 10 ? "T00:00:00" : ""));
  if (isNaN(d.getTime())) return String(v);
  const mon = d.toLocaleDateString("en-GB", { month: "short" });
  if (gran === "month") return `${mon} ${d.getFullYear()}`;
  return `${mon} ${d.getDate()}`;
}

function prevRange(dr: { start: string; end: string } | null) {
  if (!dr) return null;
  const s = new Date(dr.start + "T00:00:00");
  const e = new Date(dr.end + "T00:00:00");
  const len = Math.round((e.getTime() - s.getTime()) / 86400000) + 1;
  const pe = new Date(s); pe.setDate(s.getDate() - 1);
  const ps = new Date(pe); ps.setDate(pe.getDate() - (len - 1));
  const iso = (d: Date) => d.toISOString().split("T")[0];
  return { start: iso(ps), end: iso(pe) };
}

function delta(cur: any, prev: any): number | null {
  if (cur == null || prev == null) return null;
  const d = Number(cur) - Number(prev);
  return Number.isFinite(d) ? Math.round(d * 10) / 10 : null;
}

export default function AttendanceTab({ filters, dateRange, compare, onDrill, onOpenEmployee }: AttendanceTabProps) {
  const { data: dims } = useAnalyticsDimensions();
  const [gran, setGran] = useState("month");
  const [heatRow, setHeatRow] = useState("department");
  const [heatCol, setHeatCol] = useState("month");
  const [rankMetric, setRankMetric] = useState("absent_days");
  const [rankCount, setRankCount] = useState(10);
  const [groupDims, setGroupDims] = useState<string[]>(["department"]);
  const [groupPage, setGroupPage] = useState(1);
  const [groupPageSize] = useState(25);
  const [groupSorting, setGroupSorting] = useState<SortingState>([{ id: "attendance_rate", desc: false }]);

  // KPI totals (+ deltas)
  const totalsQ = useScopedTotals([{ domain: "attendance", metrics: ATT_METRICS }], filters, dateRange, compare);
  const t = totalsQ[0]?.data?.totals || {};
  const pt = totalsQ[0]?.data?.previous_totals || {};

  const kpis: Kpi[] = useMemo(() => [
    { label: "Attendance Rate", value: `${t.attendance_rate ?? 0}%`, delta: compare ? delta(t.attendance_rate, pt.attendance_rate) : null },
    { label: "Absence Rate", value: `${t.absence_rate ?? 0}%`, delta: compare ? delta(t.absence_rate, pt.absence_rate) : null },
    { label: "Coverage", value: `${t.coverage ?? 0}%` },
    { label: "Present Days", value: t.present_days ?? 0, delta: compare ? delta(t.present_days, pt.present_days) : null },
    { label: "Absent Days", value: t.absent_days ?? 0, delta: compare ? delta(t.absent_days, pt.absent_days) : null },
    { label: "Late Arrivals", value: t.late_arrivals ?? 0, delta: compare ? delta(t.late_arrivals, pt.late_arrivals) : null },
    { label: "Early Departures", value: t.early_departures ?? 0 },
    { label: "Incomplete", value: t.incomplete_days ?? 0 },
    { label: "Avg Work Min", value: t.avg_work_minutes ?? 0 },
  ], [t, pt, compare]);

  // Trend
  const trend = useAnalyticsExplore({
    domain: "attendance", group_by: [gran], metrics: ["attendance_rate"],
    filters, date_range: dateRange, sort_by: gran, sort_dir: "asc", page_size: 200,
  });
  const prevDr = prevRange(dateRange);
  const trendPrev = useAnalyticsExplore({
    domain: "attendance", group_by: [gran], metrics: ["attendance_rate"],
    filters, date_range: prevDr, sort_by: gran, sort_dir: "asc", page_size: 200,
  });
  const trendData: TrendPoint[] = (trend.data?.groups || []).map((g: any) => ({
    label: fmtPeriod(g[gran], gran), value: Number(g.attendance_rate ?? 0),
  }));
  const trendCompare: TrendPoint[] | undefined = compare
    ? (trendPrev.data?.groups || []).map((g: any) => ({ label: fmtPeriod(g[gran], gran), value: Number(g.attendance_rate ?? 0) }))
    : undefined;

  // Department comparison
  const byDept = useAnalyticsExplore({
    domain: "attendance", group_by: ["department"], metrics: ["attendance_rate"],
    filters, date_range: dateRange, sort_by: "attendance_rate", sort_dir: "desc", page_size: 100,
  });
  const deptData = (byDept.data?.groups || []).map((g: any) => ({ name: String(g.department ?? "—"), value: Number(g.attendance_rate ?? 0) }));

  // Heatmap
  const heat = useAnalyticsExplore({
    domain: "attendance", group_by: [heatRow, heatCol], metrics: ["attendance_rate"],
    filters, date_range: dateRange, page_size: 2000,
  });
  const heatGroups: any[] = heat.data?.groups || [];
  const rowValues = useMemo(() => Array.from(new Set(heatGroups.map((g) => fmtPeriod(String(g[heatRow]), heatRow)))), [heatGroups, heatRow]);
  const colValues = useMemo(() => Array.from(new Set(heatGroups.map((g) => fmtPeriod(String(g[heatCol]), heatCol)))), [heatGroups, heatCol]);
  const heatMap = useMemo(() => {
    const m = new Map<string, number>();
    for (const g of heatGroups) m.set(`${fmtPeriod(String(g[heatRow]), heatRow)}|${fmtPeriod(String(g[heatCol]), heatCol)}`, Number(g.attendance_rate ?? 0));
    return m;
  }, [heatGroups, heatRow, heatCol]);

  // Ranking
  const ranking = useAnalyticsExplore({
    domain: "attendance", group_by: ["employee", "employee_id"], metrics: [rankMetric],
    filters, date_range: dateRange, sort_by: rankMetric, sort_dir: "desc", page_size: rankCount,
  });
  const rankRows: any[] = ranking.data?.groups || [];

  // Group-by table
  const groupExplore = useAnalyticsExplore({
    domain: "attendance", group_by: groupDims, metrics: ["attendance_rate", "present_days", "absent_days", "late_arrivals"],
    filters, date_range: dateRange,
    sort_by: groupSorting[0]?.id || "attendance_rate",
    sort_dir: groupSorting[0]?.desc ? "desc" : "asc",
    page: groupPage, page_size: groupPageSize,
  });
  const groupColumns = (groupExplore.data?.columns || []).map((c) => ({
    key: c.key, header: c.label,
    cell: c.type === "pct" ? (r: any) => <span className="font-medium text-text-primary">{r[c.key]}%</span> : undefined,
  }));

  const dimOptions = (dims?.dimensions || []).filter((d) => ["day", "week", "month", "quarter"].includes(d.key) || d.kind === "attribute")
    .map((d) => ({ key: d.key, label: d.label }));
  const groupOptions = (dims?.dimensions || []).map((d) => ({ key: d.key, label: d.label }));

  return (
    <div className="space-y-4">
      <KpiStrip items={kpis} loading={totalsQ[0]?.isLoading} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-1 bg-nav-hover rounded-btn p-0.5 w-fit">
            {TREND_GRANS.map((g) => (
              <button
                key={g.key}
                onClick={() => setGran(g.key)}
                className={`px-3 py-1 text-xs font-medium rounded-[5px] transition-all ${
                  gran === g.key ? "bg-surface text-accent shadow-sm" : "text-text-secondary hover:text-text-primary"
                }`}
              >
                {g.label}
              </button>
            ))}
          </div>
          <TrendChart title="Attendance Rate over Time" data={trendData} compareData={trendCompare} suffix="%" loading={trend.isLoading} />
        </div>
        <CompositionChart title="Attendance Rate by Department" data={deptData} onSelect={(n) => onDrill("department", n)} loading={byDept.isLoading} />
      </div>

      <HeatmapGrid
        title="Attendance Rate Heatmap"
        rowDim={heatRow} colDim={heatCol}
        dimOptions={dimOptions}
        onRowDimChange={(k) => setHeatRow(k)} onColDimChange={(k) => setHeatCol(k)}
        rowValues={rowValues} colValues={colValues}
        value={(r, c) => heatMap.get(`${r}|${c}`) ?? null}
        suffix="%"
        loading={heat.isLoading}
        onCellClick={(r, c) => { /* labels are formatted; re-scope by row dimension only */ }}
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Ranking */}
        <div className="card-container p-4">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <h4 className="text-xs font-semibold text-text-primary">Top Staff</h4>
            <div className="flex items-center gap-1.5">
              <select value={rankMetric} onChange={(e) => setRankMetric(e.target.value)} className="px-2 py-1 text-[11px] border border-border rounded-btn bg-surface text-text-secondary cursor-pointer">
                {RANK_METRICS.map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
              </select>
              <select value={rankCount} onChange={(e) => setRankCount(Number(e.target.value))} className="px-2 py-1 text-[11px] border border-border rounded-btn bg-surface text-text-secondary cursor-pointer">
                {RANK_COUNTS.map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
          </div>
          {ranking.isLoading ? (
            <div className="space-y-2">{[...Array(6)].map((_, i) => <div key={i} className="h-7 bg-nav-hover rounded animate-pulse" />)}</div>
          ) : rankRows.length === 0 ? (
            <p className="text-xs text-text-muted text-center py-8">No data</p>
          ) : (
            <div className="space-y-1 max-h-[260px] overflow-y-auto">
              {rankRows.map((r, i) => (
                <button
                  key={r.employee_id || i}
                  onClick={() => r.employee_id && onOpenEmployee(String(r.employee_id))}
                  className="w-full flex items-center gap-2 px-2 py-1.5 rounded-btn hover:bg-nav-hover text-left"
                >
                  <span className="w-5 h-5 rounded-full bg-nav-hover text-[10px] font-bold text-text-secondary flex items-center justify-center flex-shrink-0">{i + 1}</span>
                  <span className="flex-1 text-xs text-text-primary truncate">{r.employee}</span>
                  <span className="text-xs font-semibold text-danger">{r[rankMetric]}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Group-by table */}
        <div className="space-y-2">
          <GroupByBar
            dimensions={groupOptions}
            selected={groupDims}
            max={2}
            onToggle={(k) => {
              setGroupDims((prev) => (prev.includes(k) ? prev.filter((x) => x !== k) : [...prev, k]));
              setGroupPage(1);
            }}
          />
          <DataTable
            title="Explore"
            columns={groupColumns}
            data={groupExplore.data?.groups || []}
            loading={groupExplore.isLoading}
            isFetching={groupExplore.isFetching}
            searchable={false}
            serverSide
            total={groupExplore.data?.total ?? 0}
            page={groupPage}
            pageSize={groupPageSize}
            onPageChange={setGroupPage}
            sorting={groupSorting}
            onSortingChange={(s) => { setGroupSorting(s); setGroupPage(1); }}
            onRowClick={(row: any) => {
              groupDims.forEach((d) => { if (row[d] != null) onDrill(d, String(row[d])); });
            }}
          />
        </div>
      </div>
    </div>
  );
}
