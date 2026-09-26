import { useEffect, useMemo, useState } from "react";
import type { SortingState } from "@tanstack/react-table";
import StaggerReveal, { RevealItem } from "@/components/analytics/StaggerReveal";
import KpiStrip from "@/components/analytics/KpiStrip";
import type { Kpi } from "@/components/analytics/KpiStrip";
import DataTable from "@/components/ui/DataTable";
import BarInRow from "@/components/analytics/BarInRow";
import SegmentedControl from "@/components/analytics/SegmentedControl";
import { useAnalyticsExplore, useScopedTotals, useAnalyticsMetrics } from "@/hooks/useAnalytics";
import { useManagementScope } from "@/hooks/useManagementScope";
import { semanticColor } from "@/lib/analyticsColors";
import { fmtPct, fmtNum } from "@/lib/format";
import { useTabExport } from "./exportRegistry";
import { exportToCSV } from "@/lib/csvExport";

interface PeopleTabProps {
  filters: Record<string, string[]>;
  dateRange: { start: string; end: string } | null;
  compare: boolean;
  onDrill: (dimension: string, value: string) => void;
  onOpenEmployee: (id: string) => void;
}

type EntityMode = "individuals" | "department" | "grade_level" | "rank" | "employment_type" | "zone";
const ENTITY_OPTIONS: { value: EntityMode; label: string }[] = [
  { value: "individuals", label: "Individuals" },
  { value: "department", label: "Departments" },
  { value: "grade_level", label: "Grade Levels" },
  { value: "rank", label: "Ranks" },
  { value: "employment_type", label: "Emp Types" },
  { value: "zone", label: "Zones" },
];

const ROSTER_PRESETS = [
  { key: "absent_days", label: "Absenteeism", dir: "desc" as const, color: "#FF4D4F" },
  { key: "late_arrivals", label: "Lateness", dir: "desc" as const, color: "#FAAD14" },
  { key: "incomplete_days", label: "Incomplete days", dir: "desc" as const, color: "#FA8C16" },
  { key: "leave_days", label: "Leave days", dir: "desc" as const, color: "#722ED1" },
  { key: "attendance_rate", label: "Best attendance", dir: "desc" as const, color: "#52C41A" },
  { key: "attendance_rate_low", label: "Lowest attendance", dir: "asc" as const, color: "#FF4D4F" },
];

const RANK_BADGE = ["bg-[#FFD700]/25 text-[#B8860B]", "bg-[#C0C0C0]/30 text-[#6B7280]", "bg-[#CD7F32]/25 text-[#B45309]"];

function isoDay(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
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

export default function PeopleTab({ filters, dateRange, compare, onDrill, onOpenEmployee }: PeopleTabProps) {
  const { peopleEntity: entity, setPeopleEntity: setEntity } = useManagementScope();
  const [rosterPreset, setRosterPreset] = useState(ROSTER_PRESETS[0].key);
  const [rankN, setRankN] = useState(10);

  // Directory table state
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [sorting, setSorting] = useState<SortingState>([{ id: "full_name", desc: false }]);

  useEffect(() => {
    const t = window.setTimeout(() => { setSearch(searchInput); setPage(1); }, 350);
    return () => window.clearTimeout(t);
  }, [searchInput]);

  // KPI strip
  const totals = useScopedTotals(
    [
      { domain: "employees", metrics: ["employees", "active"] },
      { domain: "attendance", metrics: ["attendance_rate", "coverage"] },
    ],
    filters, dateRange, false
  );
  const { data: metricData } = useAnalyticsMetrics();
  const ringColor = (key: string, value: unknown): string | undefined => {
    const meta = (metricData?.metrics || []).find((m) => m.key === key);
    if (!meta || meta.pivot == null || value == null || !Number.isFinite(Number(value))) return undefined;
    return semanticColor(Number(value), meta, meta.pivot, 40);
  };
  const emp = totals[0].data?.totals || {};
  const att = totals[1].data?.totals || {};
  const kpis: Kpi[] = [
    { label: "Headcount", value: emp.employees ?? 0 },
    { label: "Active", value: emp.active ?? 0 },
    { label: "Avg Attendance", value: `${att.attendance_rate ?? 0}%`, ring: att.attendance_rate ?? 0, color: ringColor("attendance_rate", att.attendance_rate), polarity: "up_good" },
    { label: "Swipe Coverage", value: `${att.coverage ?? 0}%`, ring: att.coverage ?? 0, color: ringColor("coverage", att.coverage), sub: "staff with swipe data", polarity: "up_good" },
  ];

  // ── Individuals: roster ───────────────────────────────────────────────────
  const preset = ROSTER_PRESETS.find((p) => p.key === rosterPreset) || ROSTER_PRESETS[0];
  const rosterMetric = preset.key === "attendance_rate_low" ? "attendance_rate" : preset.key;
  // Absent-day bars are colored by absence rate (30%-of-working-days rule),
  // consistent with the staff ranking and every other absent metric.
  const rosterColorByRate = rosterMetric === "absent_days";
  const roster = useAnalyticsExplore({
    domain: "attendance",
    group_by: ["employee", "employee_id", "department"],
    metrics: rosterColorByRate ? [rosterMetric, "absence_rate"] : [rosterMetric],
    filters,
    date_range: dateRange,
    sort_by: rosterMetric,
    sort_dir: preset.dir,
    page_size: rankN,
  });
  const rosterRows = (roster.data?.groups || []) as Record<string, unknown>[];
  const rosterVals = rosterRows.map((r) => Number(r[rosterMetric] ?? 0)).filter((v) => Number.isFinite(v));
  const rosterMax = Math.max(...rosterVals, 1);
  const rosterMeta = (metricData?.metrics || []).find((m) => m.key === rosterMetric);
  const absenceMeta = (metricData?.metrics || []).find((m) => m.key === "absence_rate") || { polarity: "up_bad" as const, pivot: 30 };
  const rosterScale = useMemo(() => {
    const meta = rosterMeta || { polarity: null, pivot: null };
    const pivot = meta.pivot != null ? meta.pivot : rosterVals.length ? rosterVals.reduce((s, v) => s + v, 0) / rosterVals.length : 0;
    const spread = meta.pivot != null ? 40 : Math.max(...rosterVals.map((v) => Math.abs(v - pivot)), 1);
    return (v: number) => semanticColor(v, meta, pivot, spread);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rosterMeta, rosterRows]);
  const rosterBarColor = (row: Record<string, unknown>, value: number): string => {
    if (rosterColorByRate) {
      return semanticColor(Number(row.absence_rate ?? 0), absenceMeta, absenceMeta.pivot ?? 30, 40);
    }
    return rosterScale(value);
  };

  // ── Groups: league table (merged headcount + performance) ─────────────────
  const headcount = useAnalyticsExplore({
    domain: "employees", group_by: [entity], metrics: ["employees", "active"],
    filters, page_size: 100, sort_by: "employees", sort_dir: "desc",
  });
  const perf = useAnalyticsExplore({
    domain: "attendance", group_by: [entity],
    metrics: ["attendance_rate", "absence_rate", "absent_days", "late_arrivals"],
    filters, date_range: dateRange, page_size: 100, sort_by: "attendance_rate", sort_dir: "desc",
  });
  const perfPrev = useAnalyticsExplore({
    domain: "attendance", group_by: [entity],
    metrics: ["attendance_rate"],
    filters, date_range: prevRange(dateRange), page_size: 100,
    enabled: compare && !!prevRange(dateRange),
  });

  const league = useMemo(() => {
    const rows = new Map<string, Record<string, unknown>>();
    (headcount.data?.groups || []).forEach((g: Record<string, unknown>) => {
      rows.set(String(g[entity] ?? "—"), { name: String(g[entity] ?? "—"), people: g.employees, active: g.active });
    });
    (perf.data?.groups || []).forEach((g: Record<string, unknown>) => {
      const key = String(g[entity] ?? "—");
      const row = rows.get(key) || { name: key, people: 0, active: 0 };
      row.attendance_rate = g.attendance_rate;
      row.absence_rate = g.absence_rate;
      row.absent_days = g.absent_days;
      row.late_arrivals = g.late_arrivals;
      rows.set(key, row);
    });
    if (compare) {
      const prevMap = new Map<string, number>();
      (perfPrev.data?.groups || []).forEach((g: Record<string, unknown>) => {
        prevMap.set(String(g[entity] ?? "—"), Number(g.attendance_rate ?? 0));
      });
      rows.forEach((row, key) => {
        const p = prevMap.get(key);
        row.rate_delta = p != null && row.attendance_rate != null
          ? Math.round((Number(row.attendance_rate) - p) * 10) / 10
          : null;
      });
    }
    return [...rows.values()].sort((a, b) => Number(b.people ?? 0) - Number(a.people ?? 0));
  }, [headcount.data, perf.data, perfPrev.data, entity, compare]); // eslint-disable-line react-hooks/exhaustive-deps

  const leagueMax = {
    attendance_rate: Math.max(...league.map((r) => Number(r.attendance_rate ?? 0)), 1),
    absent_days: Math.max(...league.map((r) => Number(r.absent_days ?? 0)), 1),
    late_arrivals: Math.max(...league.map((r) => Number(r.late_arrivals ?? 0)), 1),
  };

  // ── Directory (records) ───────────────────────────────────────────────────
  const directory = useAnalyticsExplore({
    domain: "employees", mode: "records",
    filters, page, page_size: pageSize, search,
    sort_by: sorting[0]?.id ?? "full_name",
    sort_dir: sorting[0]?.desc ? "desc" : "asc",
  });

  const directoryColumns = [
    { key: "id_no", header: "ID No" },
    { key: "full_name", header: "Full Name" },
    { key: "sex", header: "Sex" },
    { key: "department", header: "Department" },
    { key: "grade_level", header: "Grade Level" },
    {
      key: "status",
      header: "Status",
      cell: (r: Record<string, unknown>) => (
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
          String(r.status || "").toLowerCase() === "active"
            ? "bg-badge-green-bg text-badge-green-text"
            : "bg-nav-hover text-text-secondary"
        }`}>
          {String(r.status ?? "—")}
        </span>
      ),
    },
  ];

  useTabExport(() => {
    if (entity === "individuals") {
      exportToCSV(
        rosterRows.map((r) => ({
          id_no: r.employee_id, full_name: r.employee, [rosterMetric]: r[rosterMetric],
        })),
        `people_roster_${rosterMetric}`,
        dateRange ? { startDate: dateRange.start, endDate: dateRange.end } : undefined
      );
    } else {
      exportToCSV(league, `people_league_${entity}`, dateRange ? { startDate: dateRange.start, endDate: dateRange.end } : undefined);
    }
  });

  return (
    <StaggerReveal className="space-y-4">
      <RevealItem>
        <KpiStrip items={kpis} loading={totals.some((q) => q.isLoading)} />
      </RevealItem>

      {/* Entity switcher */}
      <RevealItem>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <SegmentedControl value={entity} options={ENTITY_OPTIONS} onChange={setEntity} />
          <p className="text-[11px] text-text-muted">
            {entity === "individuals"
              ? "Ranked by attendance behaviour in scope — click a person for the full profile."
              : "Group league table — click a row to see its people."}
          </p>
        </div>
      </RevealItem>

      {entity === "individuals" ? (
        <>
          <RevealItem>
            <div className="card-container p-4">
              <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
                <h4 className="text-xs font-semibold text-text-primary">Roster</h4>
                <div className="flex items-center gap-1.5 flex-wrap">
                  {ROSTER_PRESETS.map((p) => (
                    <button
                      key={p.key}
                      onClick={() => setRosterPreset(p.key)}
                      className={`px-2.5 py-1 text-[11px] font-medium rounded-full border transition-colors ${
                        rosterPreset === p.key
                          ? "border-accent text-accent bg-accent/5"
                          : "border-border text-text-secondary hover:bg-nav-hover"
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                  <select
                    value={rankN}
                    onChange={(e) => setRankN(Number(e.target.value))}
                    className="px-2 py-1 text-[11px] border border-border rounded-btn bg-surface text-text-secondary cursor-pointer"
                  >
                    {[10, 25, 50].map((n) => <option key={n} value={n}>{n}</option>)}
                  </select>
                </div>
              </div>
              {roster.isLoading ? (
                <div className="space-y-2">
                  {[...Array(6)].map((_, i) => <div key={i} className="h-9 bg-nav-hover rounded animate-pulse" />)}
                </div>
              ) : rosterRows.length === 0 ? (
                <p className="text-xs text-text-muted text-center py-10">No staff records in scope</p>
              ) : (
                <div className="space-y-1 max-h-[380px] overflow-y-auto">
                  {rosterRows.map((r, i) => {
                    const id = r.employee_id ? String(r.employee_id) : null;
                    const v = Number(r[rosterMetric] ?? 0);
                    const isPct = rosterMetric === "attendance_rate";
                    return (
                      <button
                        key={id || i}
                        onClick={() => id && onOpenEmployee(id)}
                        className="w-full flex items-center gap-2.5 px-2 py-2 rounded-btn hover:bg-nav-hover text-left transition-colors"
                      >
                        <span className={`w-6 h-6 rounded-full text-[10px] font-bold flex items-center justify-center flex-shrink-0 ${
                          i < 3 && preset.dir === "desc" && rosterMetric !== "attendance_rate" ? RANK_BADGE[i] : "bg-nav-hover text-text-secondary"
                        }`}>
                          {i + 1}
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block text-xs font-medium text-text-primary truncate">{String(r.employee ?? "—")}</span>
                          <span className="block text-[11px] text-text-muted">{r.employee_id ? `ID ${r.employee_id}` : ""}</span>
                        </span>
                        <BarInRow
                          value={v}
                          max={rosterMax}
                          color={rosterBarColor(r, v)}
                          barOpacity={0.4}
                          format={(n) => (isPct ? fmtPct(n) : `${fmtNum(n)} ${rosterMetric === "late_arrivals" ? "late" : "days"}`)}
                        />
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </RevealItem>

          <RevealItem>
            <DataTable
              title="Directory"
              columns={directoryColumns}
              data={(directory.data?.records || []) as Record<string, unknown>[]}
              loading={directory.isLoading}
              isFetching={directory.isFetching}
              searchable
              serverSide
              total={directory.data?.total ?? 0}
              page={page}
              pageSize={pageSize}
              pageSizeOptions={[25, 50, 100]}
              onPageChange={setPage}
              onPageSizeChange={(n) => { setPageSize(n); setPage(1); }}
              sorting={sorting}
              onSortingChange={setSorting}
              search={searchInput}
              onSearchChange={setSearchInput}
              onRowClick={(r) => r.id_no && onOpenEmployee(String(r.id_no))}
              onExport={() =>
                exportToCSV(
                  (directory.data?.records || []) as Record<string, unknown>[],
                  "people_directory",
                  dateRange ? { startDate: dateRange.start, endDate: dateRange.end } : undefined
                )
              }
            />
          </RevealItem>
        </>
      ) : (
        <RevealItem>
          <DataTable
            title="League table"
            columns={[
              { key: "name", header: ENTITY_OPTIONS.find((e) => e.value === entity)?.label || "Group" },
              { key: "people", header: "People", cell: (r) => <span className="text-xs tabular-nums">{fmtNum(Number(r.people ?? 0))}</span> },
              { key: "active", header: "Active", cell: (r) => <span className="text-xs tabular-nums">{fmtNum(Number(r.active ?? 0))}</span> },
              {
                key: "attendance_rate", header: "Attendance",
                cell: (r) => {
                  const v = Number(r.attendance_rate ?? 0);
                  const meta = { polarity: "up_good" as const, pivot: 60 };
                  return <BarInRow value={v} max={leagueMax.attendance_rate} color={semanticColor(v, meta, 60, 40)} barOpacity={0.4} format={fmtPct} />;
                },
              },
              {
                key: "absent_days", header: "Absent Days",
                cell: (r) => {
                  // Colored by the group's absence rate (30% rule), matching
                  // the staff ranking and roster.
                  const v = Number(r.absent_days ?? 0);
                  const color = semanticColor(Number(r.absence_rate ?? 0), { polarity: "up_bad", pivot: 30 }, 30, 40);
                  return <BarInRow value={v} max={leagueMax.absent_days} color={color} barOpacity={0.4} format={(n) => fmtNum(n)} />;
                },
              },
              {
                key: "late_arrivals", header: "Late",
                cell: (r) => {
                  const vals = league.map((x) => Number(x.late_arrivals ?? 0));
                  const v = Number(r.late_arrivals ?? 0);
                  const pivot = vals.length ? vals.reduce((s, x) => s + x, 0) / vals.length : 0;
                  const spread = Math.max(...vals.map((x) => Math.abs(x - pivot)), 1);
                  return <BarInRow value={v} max={leagueMax.late_arrivals} color={semanticColor(v, { polarity: "up_bad" }, pivot, spread)} barOpacity={0.4} format={(n) => fmtNum(n)} />;
                },
              },
              ...(compare
                ? [{
                    key: "rate_delta", header: "Δ Rate",
                    cell: (r: Record<string, unknown>) => {
                      const d = r.rate_delta;
                      if (d == null) return <span className="text-xs text-text-muted">—</span>;
                      const n = Number(d);
                      return (
                        <span className={`text-xs font-semibold tabular-nums ${n >= 0 ? "text-badge-green-text" : "text-badge-red-text"}`}>
                          {n >= 0 ? "+" : ""}{n}pp
                        </span>
                      );
                    },
                  }]
                : []),
            ]}
            data={league}
            loading={headcount.isLoading || perf.isLoading}
            onRowClick={(row) => {
              const name = String((row as Record<string, unknown>).name ?? "");
              if (name && name !== "—") {
                onDrill(entity, name);
                setEntity("individuals");
              }
            }}
          />
        </RevealItem>
      )}
    </StaggerReveal>
  );
}
