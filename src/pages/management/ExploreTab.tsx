import { useEffect, useMemo, useState } from "react";
import type { SortingState } from "@tanstack/react-table";
import StaggerReveal, { RevealItem } from "@/components/analytics/StaggerReveal";
import DataTable from "@/components/ui/DataTable";
import type { DateFilterValue } from "@/components/ui/DataTable";
import GroupByBar from "@/components/analytics/GroupByBar";
import MetricPicker from "@/components/analytics/MetricPicker";
import HeatmapGrid from "@/components/analytics/HeatmapGrid";
import LeaveTrendChart from "@/components/analytics/LeaveTrendChart";
import TrainingTrendChart from "@/components/analytics/TrainingTrendChart";
import BarInRow from "@/components/analytics/BarInRow";
import SegmentedControl from "@/components/analytics/SegmentedControl";
import DimmedControl from "@/components/analytics/DimmedControl";
import { useAnalyticsExplore, useAnalyticsDimensions, useAnalyticsMetrics, useMultiDomainPivot, type MetricMeta } from "@/hooks/useAnalytics";
import { makeSemanticScale, semanticColor, readableFg, STATUS_COLORS } from "@/lib/analyticsColors";
import { fmtPct, fmtNum, fmtMinutes, fmtDateFull } from "@/lib/format";
import { buildHeatOptions, TIME_DIMS } from "@/lib/heatmapPairs";
import { useTabExport } from "./exportRegistry";
import { exportToCSV } from "@/lib/csvExport";
import { api } from "@/lib/api";
import ExportIconButton from "@/components/analytics/ExportIconButton";

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

/** Leave/training rows carry start_date/end_date; the table shows one combined column. */
function formatDateRange(start: unknown, end: unknown): string {
  const sRaw = start ? String(start).slice(0, 10) : "";
  if (!sRaw) return "—";
  const s = fmtDateFull(sRaw);
  const eRaw = end ? String(end).slice(0, 10) : "";
  if (!eRaw || eRaw === sRaw) return s;
  return `${s} to ${fmtDateFull(eRaw)}`;
}

/** Raw API rows → export rows: fold start_date/end_date into one duration field. */
function rowsForExport(mode: string, rows: Record<string, unknown>[]): Record<string, unknown>[] {
  if (mode !== "leave" && mode !== "training") return rows;
  const label = mode === "leave" ? "Leave Duration" : "Training Duration";
  return rows.map((r) => {
    const { start_date, end_date, ...rest } = r as Record<string, unknown> & { start_date?: unknown; end_date?: unknown };
    return { ...rest, [label]: formatDateRange(start_date, end_date) };
  });
}

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
    { key: "date_range", header: "Leave Duration", filter: "date" },
    { key: "days_used", header: "Days Used" },
    { key: "days_unused", header: "Days Unused" },
  ],
  training: [
    { key: "id_no", header: "ID No" },
    { key: "full_name", header: "Full Name" },
    { key: "venue", header: "Venue", filter: "values" },
    { key: "consultant", header: "Consultant", filter: "values" },
    { key: "department", header: "Department", filter: "values" },
    { key: "grade_level", header: "Grade Level", filter: "values" },
    { key: "date_range", header: "Training Duration", filter: "date" },
    { key: "title", header: "Title" },
    { key: "days_used", header: "Days Used" },
    { key: "days_unused", header: "Days Unused" },
  ],
};

/** Date columns that accept sub-range filters, per record mode. */
const RECORD_DATE_KEYS: Record<string, string[]> = {
  attendance: ["work_date"],
  leave: ["date_range"],
  training: ["date_range"],
};

/** Returns a short message when a metric/group-by mix makes no sense, else null.
 * Workforce metrics (employees subject) cannot group by time dimensions —
 * that subject has no date column, so the mix is not allowed. */
function mixError(
  keys: string[],
  groups: string[],
  metaByKey: Map<string, MetricMeta>,
  dimLabel: (key: string) => string
): string | null {
  const names = keys
    .map((k) => metaByKey.get(k))
    .filter((m): m is MetricMeta => !!m && m.domain === "employees")
    .map((m) => m.label);
  if (names.length === 0) return null;
  const t = groups.find((g) => TIME_DIMS.includes(g));
  if (!t) return null;
  return `${names.join(", ")} can't be grouped by ${dimLabel(t)} — this mix is not allowed.`;
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
  const [dateFilterMode, setDateFilterMode] = useState("overlap");

  const [rankMetric, setRankMetric] = useState("absent_days");
  const [rankN, setRankN] = useState(10);
  const [rankDir, setRankDir] = useState<"top" | "bottom">("top");
  const [notice, setNotice] = useState<string | null>(null);
  // Pivot row selections: row id → group-value snapshot. Visual-only for the
  // pivot; snapshots scope the Staff ranking + heatmap (refcount semantics:
  // a value stays active while ≥1 selected row carries it).
  const [selectedPivotRows, setSelectedPivotRows] = useState<Map<string, Record<string, string>>>(new Map());

  const [heatRow, setHeatRow] = useState("department");
  const [heatCol, setHeatCol] = useState("grade_level");

  // Group-by chips: attributes first, then time grains (Day/Week/Month/Quarter).
  const groupByOptions = useMemo(() => {
    const all = dims?.dimensions || [];
    const attrs = all.filter((d) => d.kind === "attribute").map((d) => ({ key: d.key, label: d.label }));
    const time = all.filter((d) => TIME_DIMS.includes(d.key)).map((d) => ({ key: d.key, label: d.label }));
    return [...attrs, ...time];
  }, [dims]);
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

  // Auto-dismiss mix-compatibility notices
  useEffect(() => {
    if (!notice) return;
    const t = window.setTimeout(() => setNotice(null), 4000);
    return () => window.clearTimeout(t);
  }, [notice]);

  // Row identities follow the group-by: changing it (or the mode) clears
  // selections to avoid stale states.
  useEffect(() => {
    setSelectedPivotRows(new Map());
  }, [mode, groupDims]);

  // Global range broadcasts into the record-table date pickers (dashboard
  // behavior): the Duration / Work Date pickers show the global range, and
  // manual column edits diverge until the next global change. Seeded on
  // mount, so the linkage is visible from first load. Query-neutral while
  // equal — the backend's global window already implies the identical
  // overlap range — and ranking/heatmap are untouched (they follow the
  // global range directly and never read column-filter state).
  useEffect(() => {
    if (!dateRange?.start || !dateRange?.end) return;
    const v = { start: dateRange.start, end: dateRange.end };
    setDateFilters((prev) => ({ ...prev, date_range: v, work_date: v }));
    setPage(1);
  }, [dateRange?.start, dateRange?.end]);

  /** Stable id for a pivot row: its full group tuple. */
  const pivotRowId = (row: Record<string, unknown>) =>
    JSON.stringify(groupDims.map((d) => String(row[d] ?? "")));

  const togglePivotRow = (row: Record<string, unknown>) => {
    if (row.id_no) { onOpenEmployee(String(row.id_no)); return; }
    const id = pivotRowId(row);
    setSelectedPivotRows((prev) => {
      const next = new Map(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        const snap: Record<string, string> = {};
        groupDims.forEach((d) => {
          const v = row[d];
          if (v != null && String(v) !== "") snap[d] = String(v);
        });
        next.set(id, snap);
      }
      return next;
    });
  };

  const selectedPivotRowIds = useMemo(() => new Set(selectedPivotRows.keys()), [selectedPivotRows]);

  // Selection values per dimension (union across selected rows)…
  const selectionFilters = useMemo(() => {
    const out: Record<string, string[]> = {};
    for (const snap of selectedPivotRows.values()) {
      for (const [d, v] of Object.entries(snap)) {
        if (!out[d]) out[d] = [];
        if (!out[d].includes(v)) out[d].push(v);
      }
    }
    return out;
  }, [selectedPivotRows]);

  // …merged over the global scope (OR within a dimension, AND across them).
  // Only ranking + heatmap consume this; the pivot never sees it.
  const scopedFilters = useMemo(() => {
    const out: Record<string, string[]> = { ...filters };
    for (const [d, vs] of Object.entries(selectionFilters)) {
      out[d] = Array.from(new Set([...(out[d] || []), ...vs]));
    }
    return out;
  }, [filters, selectionFilters]);

  const dimLabel = (key: string) => dims?.dimensions.find((d) => d.key === key)?.label || key;

  const applyMetricKeys = (next: string[]) => {
    if (next.length === 0) return; // keep at least one metric
    const err = mixError(next, groupDims, metaByKey, dimLabel);
    if (err) { setNotice(err); return; }
    setNotice(null);
    setMetricKeys(next);
    setPage(1);
  };

  const applyGroupDims = (next: string[]) => {
    const err = mixError(metricKeys, next, metaByKey, dimLabel);
    if (err) { setNotice(err); return; }
    setNotice(null);
    setGroupDims(next);
    setPivotFilters((f) => {
      const out = { ...f };
      groupDims.forEach((g) => { if (!next.includes(g)) delete out[g]; });
      return out;
    });
    setPage(1);
  };

  // Keep the default sort column valid when the metric set changes
  const sortId = sorting[0]?.id && (metricKeys.includes(sorting[0].id) || groupDims.includes(sorting[0].id))
    ? sorting[0].id
    : metricKeys[0];

  const pivotFiltersApi = useMemo(() => {
    const out: Record<string, string[]> = {};
    for (const [k, s] of Object.entries(pivotFilters)) if (s.size > 0) out[k] = [...s];
    return out;
  }, [pivotFilters]);

  // Metrics may span subjects: single subject → one server query,
  // mixed subjects → one query per subject, merged on the group key.
  const metricDomains = useMemo(
    () => Array.from(new Set(metricKeys.map((k) => metaByKey.get(k)?.domain || "attendance"))),
    [metricKeys, metaByKey]
  );
  const isMixed = metricDomains.length > 1;
  const metricsByDomain = useMemo(
    () =>
      metricDomains.map((d) => ({
        domain: d as "attendance" | "leave" | "training" | "employees",
        metrics: metricKeys.filter((k) => (metaByKey.get(k)?.domain || "attendance") === d),
      })),
    [metricDomains, metricKeys, metaByKey]
  );

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
    enabled: isSummary && !isMixed,
  });
  const multiPivot = useMultiDomainPivot({
    metricsByDomain,
    group_by: groupDims,
    filters: { ...filters, ...pivotFiltersApi },
    date_range: dateRange,
    enabled: isSummary && isMixed,
  });
  const pivotRows: Record<string, unknown>[] = isMixed ? multiPivot.rows : ((pivot.data?.groups || []) as Record<string, unknown>[]);

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
    date_filter_mode: dateFilterMode,
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
    filters: scopedFilters,
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
    filters: scopedFilters,
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
    const rows = pivotRows;
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
  }, [pivotRows, metricKeys, metaByKey]);

  const summaryColumns = useMemo(() => {
    if (!isSummary) return [];
    const dimCols = groupDims.map((g) => ({
      key: g,
      header: dims?.dimensions.find((d) => d.key === g)?.label || g,
      filter: "values" as const,
      // Time grains have no value-option list — no filter icon
      filterable: !TIME_DIMS.includes(g),
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
        if (c.key === "date_range") return <span className="text-xs tabular-nums whitespace-nowrap">{formatDateRange(row.start_date, row.end_date)}</span>;
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

  const mapPivotGroups = (groups: Record<string, unknown>[]) =>
    groups.map((g) => {
      const out: Record<string, unknown> = {};
      groupDims.forEach((d) => { out[dims?.dimensions.find((x) => x.key === d)?.label || d] = g[d]; });
      metricKeys.forEach((k) => { out[metaByKey.get(k)?.label || k] = g[k]; });
      return out;
    });
  const exportPivotRange = dateRange ? { startDate: dateRange.start, endDate: dateRange.end } : undefined;

  // Full-set pivot export (the table page is only a window into it; mixed
  // pivots already hold all groups client-side).
  const exportPivotFull = async () => {
    try {
      if (isMixed) {
        exportToCSV(mapPivotGroups(pivotRows), `explore_${subject}_mixed`, exportPivotRange);
        return;
      }
      const res = await api.post("/api/analytics/explore", {
        domain: subject,
        metrics: metricKeys,
        group_by: groupDims,
        mode: "summary",
        filters: { ...filters, ...pivotFiltersApi },
        date_range: dateRange,
        page: 1,
        page_size: 2000,
        sort_by: sortId,
        sort_dir: sorting[0]?.desc === false ? "asc" : "desc",
      });
      exportToCSV(mapPivotGroups(res.data?.groups || []), `explore_${subject}`, exportPivotRange);
    } catch {
      /* ignore export errors */
    }
  };

  // Full-set records export (table page is only a window into it; capped at
  // 2000 rows so unfiltered attendance sweeps can't hang the browser).
  const exportRecordsFull = async () => {
    try {
      const res = await api.post("/api/analytics/explore", {
        domain: mode === "summary" ? "attendance" : mode,
        mode: "records",
        filters,
        date_range: dateRange,
        page: 1,
        page_size: 2000,
        search,
        sort_by: sorting[0]?.id || "",
        sort_dir: sorting[0]?.desc === false ? "asc" : "desc",
        record_filters: recordFiltersApi,
        date_sub_ranges: dateSubRanges,
        date_filter_mode: dateFilterMode,
      });
      exportToCSV(
        rowsForExport(mode, (res.data?.records || []) as Record<string, unknown>[]),
        `explore_${mode}`,
        exportPivotRange
      );
    } catch {
      /* ignore export errors */
    }
  };

  useTabExport(() => {
    const rows = isSummary
      ? mapPivotGroups(pivotRows)
      : rowsForExport(mode, (records.data?.records || []) as Record<string, unknown>[]);
    exportToCSV(rows as Record<string, unknown>[], `explore_${isSummary ? subject : mode}`, dateRange ? { startDate: dateRange.start, endDate: dateRange.end } : undefined);
  });

  return (
    <StaggerReveal className="space-y-4">
      {/* Builder bar */}
      <RevealItem>
        <div className="card-container p-3 flex items-center gap-2 flex-wrap">
          {isSummary ? (
            <GroupByBar
              dimensions={groupByOptions}
              selected={groupDims}
              max={3}
              onToggle={(k) => {
                const next = groupDims.includes(k)
                  ? groupDims.filter((x) => x !== k)
                  : [...groupDims, k].slice(0, 3);
                applyGroupDims(next);
              }}
            />
          ) : (
            <DimmedControl reason="Group-by shapes the Summary pivot — switch to Summary to use it">
              <GroupByBar
                dimensions={groupByOptions}
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
                const next = Array.isArray(k)
                  ? k
                  : metricKeys.includes(k)
                    ? metricKeys.filter((x) => x !== k)
                    : [...metricKeys, k];
                applyMetricKeys(next);
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
      {notice && (
        <p className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded-btn px-2.5 py-1.5">
          {notice}
        </p>
      )}

      {/* Pivot or records table */}
      <RevealItem>
        {isSummary ? (
          <DataTable
            title={isMixed ? "Pivot (mixed subjects)" : "Pivot"}
            columns={summaryColumns}
            data={pivotRows as Record<string, unknown>[]}
            loading={isMixed ? multiPivot.loading : pivot.isLoading}
            isFetching={isMixed ? multiPivot.isFetching : pivot.isFetching}
            searchable={false}
            enableColumnFilters
            csvExportName={`explore_${subject}_pivot`}
            onExport={() => { void exportPivotFull(); }}
            serverSide={!isMixed}
            total={isMixed ? undefined : pivot.data?.total ?? 0}
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
            getRowId={(row) => pivotRowId(row as Record<string, unknown>)}
            selectedRowIds={selectedPivotRowIds}
            onRowClick={(row) => togglePivotRow(row as Record<string, unknown>)}
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
            dateFilterBounds={mode === "attendance" && dateRange ? { min: dateRange.start, max: dateRange.end } : undefined}
            centeredDateFilter={mode === "leave" || mode === "training" ? ["date_range"] : false}
            dateFilterMode={dateFilterMode}
            onDateFilterModeChange={(m) => { setDateFilterMode(m); setPage(1); }}
            onRowClick={(row) => {
              const r = row as Record<string, unknown>;
              if (r.id_no) onOpenEmployee(String(r.id_no));
            }}
            csvExportName={`explore_${mode}`}
            onExport={() => { void exportRecordsFull(); }}
          />
        )}
      </RevealItem>

      {/* Leave time series directly below the Leave table (own range + legend toggles) */}
      {!isSummary && mode === "leave" && (
        <RevealItem>
          <LeaveTrendChart filters={filters} initialRange={dateRange} />
        </RevealItem>
      )}

      {/* Training time series directly below the Training table (own range + legend toggles) */}
      {!isSummary && mode === "training" && (
        <RevealItem>
          <TrainingTrendChart filters={filters} initialRange={dateRange} />
        </RevealItem>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Rankings */}
        <RevealItem>
          <div className="card-container p-4">
            <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
              <h4 className="text-xs font-semibold text-text-primary">Staff ranking</h4>
              <div className="flex items-center gap-1.5">
                <ExportIconButton
                  onExport={() =>
                    exportToCSV(
                      rankRows.map((r) => ({
                        id_no: r.employee_id ?? "",
                        full_name: r.employee ?? "",
                        department: r.department ?? "",
                        [rankMeta?.label || rankMetric]: r[rankMetric] ?? "",
                      })),
                      `explore_ranking_${rankMetric}`,
                      exportPivotRange
                    )
                  }
                />
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
            title="Cross dimension heatmap"
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
            onExport={() =>
              exportToCSV(
                heatRowVals.flatMap((r) =>
                  heatColVals.map((c) => ({
                    [dimLabel(heatRow)]: r,
                    [dimLabel(heatCol)]: c,
                    [heatMeta?.label || heatMetric]: heatMap.get(`${r}|${c}`) ?? "",
                  }))
                ),
                "explore_heatmap",
                exportPivotRange
              )
            }
          />
        </RevealItem>
      </div>
    </StaggerReveal>
  );
}
