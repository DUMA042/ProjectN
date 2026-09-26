import { useEffect, useMemo, useState } from "react";
import type { SortingState } from "@tanstack/react-table";
import StaggerReveal, { RevealItem } from "@/components/analytics/StaggerReveal";
import DataTable from "@/components/ui/DataTable";
import type { DateFilterValue } from "@/components/ui/DataTable";
import GroupByBar from "@/components/analytics/GroupByBar";
import MetricPicker from "@/components/analytics/MetricPicker";
import HeatmapGrid from "@/components/analytics/HeatmapGrid";
import BarInRow from "@/components/analytics/BarInRow";
import SegmentedControl from "@/components/analytics/SegmentedControl";
import DimmedControl from "@/components/analytics/DimmedControl";
import { useAnalyticsExplore, useAnalyticsDimensions, useAnalyticsMetrics, type MetricMeta } from "@/hooks/useAnalytics";
import { makeSemanticScale, semanticColor, readableFg, STATUS_COLORS } from "@/lib/analyticsColors";
import { fmtPct, fmtNum, fmtMinutes, fmtDateFull } from "@/lib/format";
import { buildHeatOptions, TIME_DIMS } from "@/lib/heatmapPairs";
import { useTabExport } from "./exportRegistry";
import { exportToCSV } from "@/lib/csvExport";

interface ExploreTabProps {
  filters: Record<string, string[]>;
  dateRange: { start: string; end: string } | null;
  onDrill: (dimension: string, value: string) => void;
  onOpenEmployee: (id: string) => void;
}

const MODES = [
  { value: "summary", label: "Summary" },
  { value: "attendance", label: "Attendance record" },
  { value: "leave", label: "Leave" },
  { value: "training", label: "Training" },
] as const;
type Mode = (typeof MODES)[number]["value"];

const DEFAULT_PIVOT_METRICS = ["attendance_rate", "present_days", "absent_days", "late_arrivals"];

/** Record table column definitions per record domain. */
const RECORD_COLUMNS: Record<string, { key: string; header: string; filter?: "values" | "date"; kind?: "date" | "minutes" | "status" }[]> = {
  attendance: [
    { key: "id_no", header: "ID No" },
    { key: "full_name", header: "Full Name" },
    { key: "work_date", header: "Work Date", filter: "date", kind: "date" },
    { key: "status", header: "Status", filter: "values", kind: "status" },
    { key: "checkin_time", header: "Check-in" },
    { key: "checkin_status", header: "Check-in Status", filter: "values" },
    { key: "checkout_time", header: "Check-out" },
    { key: "checkout_status", header: "Check-out Status", filter: "values" },
    { key: "minutes_worked", header: "Minutes Worked", kind: "minutes" },
  ],
  leave: [
    { key: "id_no", header: "ID No" },
    { key: "full_name", header: "Full Name" },
    { key: "leave_type", header: "Leave Type", filter: "values" },
    { key: "department", header: "Department", filter: "values" },
    { key: "grade_level", header: "Grade Level", filter: "values" },
    { key: "start_date", header: "Start Date", filter: "date", kind: "date" },
    { key: "end_date", header: "End Date", filter: "date", kind: "date" },
  ],
  training: [
    { key: "id_no", header: "ID No" },
    { key: "full_name", header: "Full Name" },
    { key: "venue", header: "Venue", filter: "values" },
    { key: "consultant", header: "Consultant", filter: "values" },
    { key: "department", header: "Department", filter: "values" },
    { key: "grade_level", header: "Grade Level", filter: "values" },
    { key: "start_date", header: "Start Date", filter: "date", kind: "date" },
    { key: "end_date", header: "End Date", filter: "date", kind: "date" },
    { key: "title", header: "Title" },
  ],
};

/** Date columns that accept sub-range filters, per record mode. */
const RECORD_DATE_KEYS: Record<string, string[]> = {
  attendance: ["work_date"],
  leave: ["start_date", "end_date"],
  training: ["start_date", "end_date"],
};

const RECORD_DATE_KEY: Record<string, string> = {
  attendance: "work_date",
  leave: "start_date",
  training: "start_date",
};

/** Enforce "one subject per pivot": a metric from another subject resets the selection. */
function reconcileMetrics(current: string[], picked: string, meta: MetricMeta[] | undefined): string[] {
  const m = meta?.find((x) => x.key === picked);
  if (!m) return current;
  const currentDomain = meta?.find((x) => x.key === current[0])?.domain;
  if (!currentDomain || currentDomain === m.domain) {
    return current.includes(picked) ? current.filter((k) => k !== picked) : [...current, picked];
  }
  return [picked];
}

export default function ExploreTab({ filters, dateRange, onDrill, onOpenEmployee }: ExploreTabProps) {
  const { data: dims } = useAnalyticsDimensions();
  const { data: metricData } = useAnalyticsMetrics();
  const allMetrics: MetricMeta[] = metricData?.metrics || [];
  const metaByKey = useMemo(() => new Map(allMetrics.map((m) => [m.key, m])), [allMetrics]);

  const [mode, setMode] = useState<Mode>("summary");
  const [groupDims, setGroupDims] = useState<string[]>(["department"]);
  const [metricKeys, setMetricKeys] = useState<string[]>(DEFAULT_PIVOT_METRICS);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [sorting, setSorting] = useState<SortingState>([{ id: "attendance_rate", desc: true }]);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [pivotFilters, setPivotFilters] = useState<Record<string, Set<string>>>({});
  const [recordFilters, setRecordFilters] = useState<Record<string, Set<string>>>({});
  const [dateFilters, setDateFilters] = useState<Record<string, DateFilterValue | undefined>>({});

  const [rankMetric, setRankMetric] = useState("absent_days");
  const [rankN, setRankN] = useState(10);
  const [rankDir, setRankDir] = useState<"top" | "bottom">("top");

  const [heatRow, setHeatRow] = useState("department");
  const [heatCol, setHeatCol] = useState("grade_level");

  const attrOptions = (dims?.dimensions || [])
    .filter((d) => d.kind === "attribute")
    .map((d) => ({ key: d.key, label: d.label }));
  const subject = allMetrics.find((m) => m.key === metricKeys[0])?.domain || "attendance";
  const isSummary = mode === "summary";

  // Reset record-scoped state when switching modes
  useEffect(() => {
    setPage(1);
    setRecordFilters({});
    setDateFilters({});
    setSorting(isSummary ? [{ id: metricKeys[0] || "attendance_rate", desc: true }] : []);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  useEffect(() => {
    const t = window.setTimeout(() => { setSearch(searchInput); setPage(1); }, 350);
    return () => window.clearTimeout(t);
  }, [searchInput]);

  // Keep the default sort column valid when the metric set changes
  const sortId = sorting[0]?.id && (metricKeys.includes(sorting[0].id) || groupDims.includes(sorting[0].id))
    ? sorting[0].id
    : metricKeys[0];

  const pivotFiltersApi = useMemo(() => {
    const out: Record<string, string[]> = {};
    for (const [k, s] of Object.entries(pivotFilters)) if (s.size > 0) out[k] = [...s];
    return out;
  }, [pivotFilters]);

  // ── Pivot (summary) query ─────────────────────────────────────────────────
  const pivot = useAnalyticsExplore({
    domain: subject,
    metrics: metricKeys,
    group_by: groupDims,
    mode: "summary",
    filters: { ...filters, ...pivotFiltersApi },
    date_range: dateRange,
    page,
    page_size: pageSize,
    sort_by: sortId,
    sort_dir: sorting[0]?.desc === false ? "asc" : "desc",
    enabled: isSummary,
  });

  // ── Records query (Attendance record / Leave / Training) ──────────────────
  const dateSubRanges = useMemo(() => {
    const allowed = RECORD_DATE_KEYS[mode] || [];
    const out: Record<string, { start: string; end: string }> = {};
    for (const [k, v] of Object.entries(dateFilters)) {
      if (v && allowed.includes(k)) out[k] = { start: v.start, end: v.end };
    }
    return out;
  }, [dateFilters, mode]);
  const recordFiltersApi = useMemo(() => {
    const out: Record<string, string[]> = {};
    for (const [k, s] of Object.entries(recordFilters)) if (s.size > 0) out[k] = [...s];
    return out;
  }, [recordFilters]);

  const records = useAnalyticsExplore({
    domain: mode === "summary" ? "attendance" : mode,
    mode: "records",
    filters,
    date_range: dateRange,
    page,
    page_size: pageSize,
    search,
    sort_by: sorting[0]?.id || "",
    sort_dir: sorting[0]?.desc === false ? "asc" : "desc",
    record_filters: recordFiltersApi,
    date_sub_ranges: dateSubRanges,
    enabled: !isSummary,
  });

  // ── Staff ranking (semantic-colored, with ID + department) ────────────────
  // Absent-day bars are colored by the employee's absence rate against the
  // 30%-of-working-days rule, consistent with every other absent metric.
  const rankColorByRate = rankMetric === "absent_days";
  const ranking = useAnalyticsExplore({
    domain: "attendance",
    group_by: ["employee", "employee_id", "department"],
    metrics: rankColorByRate ? [rankMetric, "absence_rate"] : [rankMetric],
    filters,
    date_range: dateRange,
    sort_by: rankMetric,
    sort_dir: rankDir === "top" ? "desc" : "asc",
    page_size: rankN,
  });

  // ── Dimension × dimension heatmap (curated pairs) ─────────────────────────
  const heatMetric = metricKeys[0];
  const heat = useAnalyticsExplore({
    domain: subject,
    group_by: [heatRow, heatCol],
    metrics: [heatMetric],
    filters,
    date_range: dateRange,
    page_size: 2000,
  });
  const heatGroups: Record<string, unknown>[] = heat.data?.groups || [];
  const heatRowVals = useMemo(() => Array.from(new Set(heatGroups.map((g) => String(g[heatRow] ?? "—")))), [heatGroups, heatRow]);
  const heatColVals = useMemo(() => Array.from(new Set(heatGroups.map((g) => String(g[heatCol] ?? "—")))), [heatGroups, heatCol]);
  const heatMap = useMemo(() => {
    const m = new Map<string, number>();
    heatGroups.forEach((g) => m.set(`${String(g[heatRow] ?? "—")}|${String(g[heatCol] ?? "—")}`, Number(g[heatMetric] ?? 0)));
    return m;
  }, [heatGroups, heatRow, heatCol, heatMetric]);
  const heatMeta = metaByKey.get(heatMetric);
  const heatCellColor = useMemo(() => {
    if (!heatMeta) return undefined;
    const scale = makeSemanticScale(heatMeta, [...heatMap.values()]);
    return (v: number) => {
      const bg = scale(v);
      return { bg, fg: readableFg(bg) };
    };
  }, [heatMeta, heatMap]);

  // Column scaling for pivot heat tints (semantic blue↔red)
  const scaleByMetric = useMemo(() => {
    const rows = pivot.data?.groups || [];
    const out: Record<string, (v: number) => { bg: string; fg: string }> = {};
    metricKeys.forEach((k) => {
      const meta = metaByKey.get(k);
      if (!meta) return;
      const vals = rows.map((r) => Number(r[k])).filter((v) => Number.isFinite(v));
      const scale = makeSemanticScale(meta, vals);
      out[k] = (v: number) => {
        const bg = scale(v);
        return { bg, fg: readableFg(bg) };
      };
    });
    return out;
  }, [pivot.data, metricKeys, metaByKey]);

  const summaryColumns = useMemo(() => {
    if (!isSummary) return [];
    const dimCols = groupDims.map((g) => ({
      key: g,
      header: dims?.dimensions.find((d) => d.key === g)?.label || g,
      filter: "values" as const,
    }));
    const metricCols = metricKeys.map((k) => {
      const meta = metaByKey.get(k);
      const colorOf = scaleByMetric[k];
      return {
        key: k,
        header: meta?.label || k,
        filterable: false,
        cell: (row: Record<string, unknown>) => {
          const v = Number(row[k]);
          if (!Number.isFinite(v)) return <span className="text-text-muted">—</span>;
          const fill = colorOf ? colorOf(v) : { bg: "transparent", fg: "#0F172A" };
          return (
            <div className="rounded-[3px] px-2 py-1 -my-1 inline-block min-w-[56px] text-center" style={{ backgroundColor: fill.bg }}>
              <span className="text-xs font-medium tabular-nums" style={{ color: fill.fg }}>
                {meta?.type === "pct" ? fmtPct(v) : fmtNum(v)}
              </span>
            </div>
          );
        },
      };
    });
    return [...dimCols, ...metricCols];
  }, [isSummary, groupDims, metricKeys, dims, metaByKey, scaleByMetric]);

  const recordColumnDefs = useMemo(() => {
    if (isSummary) return [];
    const defs = RECORD_COLUMNS[mode] || [];
    return defs.map((c) => ({
      key: c.key,
      header: c.header,
      filter: c.filter,
      cell: (row: Record<string, unknown>) => {
        const v = row[c.key];
        if (c.kind === "date") return <span className="text-xs tabular-nums whitespace-nowrap">{v ? fmtDateFull(String(v)) : "—"}</span>;
        if (c.kind === "minutes") return <span className="text-xs tabular-nums">{fmtMinutes(Number(v))}</span>;
        if (c.kind === "status") {
          const color = STATUS_COLORS[String(v || "").toLowerCase()];
          return (
            <span className="flex items-center gap-1.5 text-xs">
              {color && <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />}
              {String(v ?? "—")}
            </span>
          );
        }
        return v != null ? String(v) : "—";
      },
    }));
  }, [isSummary, mode]);

  const rankMeta = metaByKey.get(rankMetric);
  const rankRows = (ranking.data?.groups || []) as Record<string, unknown>[];
  const rankVals = rankRows.map((r) => Number(r[rankMetric] ?? 0)).filter((v) => Number.isFinite(v));
  const rankMax = Math.max(...rankVals, 1);
  const rankScale = useMemo(() => makeSemanticScale(rankMeta || {}, rankVals), [rankMeta, rankVals]); // eslint-disable-line react-hooks/exhaustive-deps
  const absenceMeta = metaByKey.get("absence_rate") || { polarity: "up_bad" as const, pivot: 30 };
  const rankBarColor = (row: Record<string, unknown>, value: number): string => {
    if (rankColorByRate) {
      return semanticColor(Number(row.absence_rate ?? 0), absenceMeta, absenceMeta.pivot ?? 30, 40);
    }
    return rankScale(value);
  };

  const filterOptions = isSummary
    ? Object.fromEntries(groupDims.map((g) => [g, (dims?.options?.[g] || []).map(String)]))
    : records.data?.filter_options || {};

  const heatOpts = useMemo(
    () => buildHeatOptions((dims?.dimensions || []).map((d) => ({ key: d.key, label: d.label }))),
    [dims]
  );

  useTabExport(() => {
    const rows = isSummary
      ? (pivot.data?.groups || []).map((g) => {
          const out: Record<string, unknown> = {};
          groupDims.forEach((d) => { out[dims?.dimensions.find((x) => x.key === d)?.label || d] = g[d]; });
          metricKeys.forEach((k) => { out[metaByKey.get(k)?.label || k] = g[k]; });
          return out;
        })
      : (records.data?.records || []);
    exportToCSV(rows as Record<string, unknown>[], `explore_${isSummary ? subject : mode}`, dateRange ? { startDate: dateRange.start, endDate: dateRange.end } : undefined);
  });

  return (
    <StaggerReveal className="space-y-4">
      {/* Builder bar */}
      <RevealItem>
        <div className="card-container p-3 flex items-center gap-2 flex-wrap">
          {isSummary ? (
            <GroupByBar
              dimensions={attrOptions.filter((o) => !TIME_DIMS.includes(o.key))}
              selected={groupDims}
              max={3}
              onToggle={(k) => {
                setGroupDims((prev) => (prev.includes(k) ? prev.filter((x) => x !== k) : [...prev, k].slice(0, 3)));
                setPivotFilters((f) => {
                  const next = { ...f };
                  delete next[k];
                  return next;
                });
                setPage(1);
              }}
            />
          ) : (
            <DimmedControl reason="Group-by shapes the Summary pivot — switch to Summary to use it">
              <GroupByBar
                dimensions={attrOptions.filter((o) => !TIME_DIMS.includes(o.key))}
                selected={groupDims}
                max={3}
                onToggle={() => {}}
              />
            </DimmedControl>
          )}
          {isSummary ? (
            <MetricPicker
              multi
              value={metricKeys}
              onChange={(k) => {
                if (Array.isArray(k)) return;
                setMetricKeys((cur) => reconcileMetrics(cur, k, allMetrics));
                setPage(1);
              }}
              label="Metrics"
            />
          ) : (
            <DimmedControl reason="Metrics drive the Summary pivot — switch to Summary to use them">
              <MetricPicker multi value={metricKeys} onChange={() => {}} label="Metrics" />
            </DimmedControl>
          )}
          <div className="ml-auto flex items-center gap-2">
            {isSummary ? (
              <DimmedControl reason="Search finds records — switch to a record view to use it">
                <input
                  value=""
                  readOnly
                  placeholder="Search records…"
                  className="px-2.5 py-1.5 text-xs border border-border rounded-input bg-surface text-text-primary placeholder-text-muted w-44"
                />
              </DimmedControl>
            ) : (
              <input
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search records…"
                className="px-2.5 py-1.5 text-xs border border-border rounded-input bg-surface text-text-primary placeholder-text-muted focus:outline-none focus:border-accent w-44"
              />
            )}
            <SegmentedControl
              value={mode}
              options={MODES.map((m) => ({ value: m.value, label: m.label }))}
              onChange={(m) => setMode(m as Mode)}
            />
          </div>
        </div>
      </RevealItem>

      {/* Pivot or records table */}
      <RevealItem>
        {isSummary ? (
          <DataTable
            title="Pivot"
            columns={summaryColumns}
            data={(pivot.data?.groups || []) as Record<string, unknown>[]}
            loading={pivot.isLoading}
            isFetching={pivot.isFetching}
            searchable={false}
            enableColumnFilters
            serverSide
            total={pivot.data?.total ?? 0}
            page={page}
            pageSize={pageSize}
            pageSizeOptions={[25, 50, 100]}
            onPageChange={setPage}
            onPageSizeChange={(n) => { setPageSize(n); setPage(1); }}
            sorting={sorting}
            onSortingChange={(s) => { setSorting(s); setPage(1); }}
            columnFilters={pivotFilters}
            onColumnFiltersChange={(f) => { setPivotFilters(f); setPage(1); }}
            filterOptions={filterOptions}
            onRowClick={(row) => {
              const r = row as Record<string, unknown>;
              if (r.id_no) { onOpenEmployee(String(r.id_no)); return; }
              groupDims.forEach((d) => {
                if (r[d] != null && !TIME_DIMS.includes(d)) onDrill(d, String(r[d]));
              });
            }}
          />
        ) : (
          <DataTable
            title={MODES.find((m) => m.value === mode)?.label}
            columns={recordColumnDefs}
            data={(records.data?.records || []) as Record<string, unknown>[]}
            loading={records.isLoading}
            isFetching={records.isFetching}
            searchable
            enableColumnFilters
            serverSide
            total={records.data?.total ?? 0}
            page={page}
            pageSize={pageSize}
            pageSizeOptions={[25, 50, 100]}
            onPageChange={setPage}
            onPageSizeChange={(n) => { setPageSize(n); setPage(1); }}
            sorting={sorting}
            onSortingChange={(s) => { setSorting(s); setPage(1); }}
            search={searchInput}
            onSearchChange={setSearchInput}
            columnFilters={recordFilters}
            onColumnFiltersChange={(f) => { setRecordFilters(f); setPage(1); }}
            filterOptions={filterOptions}
            dateFilters={dateFilters}
            onDateFiltersChange={(f) => { setDateFilters(f); setPage(1); }}
            dateFilterBounds={dateRange ? { min: dateRange.start, max: dateRange.end } : undefined}
            onRowClick={(row) => {
              const r = row as Record<string, unknown>;
              if (r.id_no) onOpenEmployee(String(r.id_no));
            }}
            onExport={() =>
              exportToCSV(
                (records.data?.records || []) as Record<string, unknown>[],
                `explore_${mode}`,
                dateRange ? { startDate: dateRange.start, endDate: dateRange.end } : undefined
              )
            }
          />
        )}
      </RevealItem>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Rankings */}
        <RevealItem>
          <div className="card-container p-4">
            <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
              <h4 className="text-xs font-semibold text-text-primary">Staff ranking</h4>
              <div className="flex items-center gap-1.5">
                <MetricPicker
                  value={rankMetric}
                  onChange={(k) => setRankMetric(Array.isArray(k) ? (k[0] || "absent_days") : k)}
                  domains={["attendance"]}
                />
                <select
                  value={rankDir}
                  onChange={(e) => setRankDir(e.target.value as "top" | "bottom")}
                  className="px-2 py-1 text-[11px] border border-border rounded-btn bg-surface text-text-secondary cursor-pointer"
                >
                  <option value="top">Top</option>
                  <option value="bottom">Bottom</option>
                </select>
                <select
                  value={rankN}
                  onChange={(e) => setRankN(Number(e.target.value))}
                  className="px-2 py-1 text-[11px] border border-border rounded-btn bg-surface text-text-secondary cursor-pointer"
                >
                  {[5, 10, 25, 50].map((n) => <option key={n} value={n}>{n}</option>)}
                </select>
              </div>
            </div>
            {ranking.isLoading ? (
              <div className="space-y-2">
                {[...Array(6)].map((_, i) => <div key={i} className="h-9 bg-nav-hover rounded animate-pulse" />)}
              </div>
            ) : rankRows.length === 0 ? (
              <p className="text-xs text-text-muted text-center py-8">No data</p>
            ) : (
              <div className="space-y-1 max-h-[300px] overflow-y-auto">
                {rankRows.map((r, i) => {
                  const id = r.employee_id ? String(r.employee_id) : null;
                  const v = Number(r[rankMetric] ?? 0);
                  return (
                    <button
                      key={`${r.employee_id || i}`}
                      onClick={() => id && onOpenEmployee(id)}
                      className="w-full flex items-center gap-2.5 px-2 py-1.5 rounded-btn hover:bg-nav-hover text-left transition-colors"
                    >
                      <span className="w-5 h-5 rounded-full bg-nav-hover text-[10px] font-bold text-text-secondary flex items-center justify-center flex-shrink-0">
                        {i + 1}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="flex items-center gap-1.5 min-w-0">
                          <span className="text-xs font-medium text-text-primary truncate">{String(r.employee ?? "—")}</span>
                          {id && (
                            <span className="text-[10px] text-text-muted bg-nav-hover rounded px-1 py-px flex-shrink-0">ID {id}</span>
                          )}
                        </span>
                        <span className="block text-[11px] text-text-muted truncate">{String(r.department ?? "—")}</span>
                      </span>
                      <BarInRow
                        value={v}
                        max={rankMax}
                        color={rankBarColor(r, v)}
                        barOpacity={0.4}
                        format={(n) => (rankMeta?.type === "pct" ? fmtPct(n) : fmtNum(n))}
                      />
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </RevealItem>

        {/* Dimension × dimension heatmap */}
        <RevealItem>
          <HeatmapGrid
            title="Cross-dimension heatmap"
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
            rowValues={heatRowVals} colValues={heatColVals}
            value={(r, c) => heatMap.get(`${r}|${c}`) ?? null}
            suffix={heatMeta?.type === "pct" ? "%" : ""}
            loading={heat.isLoading}
            cellColor={heatCellColor}
          />
        </RevealItem>
      </div>
    </StaggerReveal>
  );
}
