import { useState, useEffect, useCallback, useMemo } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { X, Building2, User, Briefcase, Clock, Check } from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import type { SortingState } from "@tanstack/react-table";
import { api } from "@/lib/api";
import DateRangePicker, { getDefaultDateRange } from "@/components/ui/DateRangePicker";
import type { DateRange } from "@/components/ui/DateRangePicker";
import DataTable from "@/components/ui/DataTable";
import { useEmployeeRecords } from "@/hooks/useDashboard";

interface EmployeeDetailSheetProps {
  employeeId: string;
  onClose: () => void;
  defaultDateRange?: DateRange;
}

type TabKey = "attendance" | "leave" | "training";

interface TabState {
  page: number;
  pageSize: number;
  searchInput: string;
  search: string;
  sorting: SortingState;
  filters: Record<string, Set<string>>;
}

const DEFAULT_SORT: Record<TabKey, string> = {
  attendance: "day_date",
  leave: "start_date",
  training: "start_date",
};

function makeTabState(sortId: string): TabState {
  return { page: 1, pageSize: 10, searchInput: "", search: "", sorting: [{ id: sortId, desc: true }], filters: {} };
}

// Full 24h Y-axis ticks every 4 hours
const FULL_DAY_TICKS = [0, 240, 480, 720, 960, 1200, 1440];

function parseTimeMinutes(s: string): number {
  const [h, m] = s.split(":").map(Number);
  return (h || 0) * 60 + (m || 0);
}

function dayNameOf(dateStr: string): string {
  const d = new Date(dateStr + "T12:00:00");
  return ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"][d.getDay()];
}

function resolveDayThresholds(workingHours: any, dates: string[], kind: "checkin" | "checkout") {
  if (!workingHours) return null;
  for (const ds of dates) {
    const wh = workingHours[dayNameOf(ds)];
    if (wh && wh[kind]) return wh[kind];
  }
  for (const dn of ["monday", "tuesday", "wednesday", "thursday", "friday"]) {
    const wh = workingHours[dn];
    if (wh && wh[kind]) return wh[kind];
  }
  return null;
}

function colorForTime(minutes: number, thresholds: any): string {
  if (!thresholds) return "#1677FF";
  const earlyBefore = thresholds.early_before ? parseTimeMinutes(thresholds.early_before) : null;
  const lateAfter = thresholds.late_after ? parseTimeMinutes(thresholds.late_after) : null;
  if (earlyBefore !== null && minutes < earlyBefore) return "#52C41A";
  if (lateAfter !== null && minutes > lateAfter) return "#FF4D4F";
  return "#1677FF";
}

function AttrRow({ icon: Icon, label, value }: { icon: any; label: string; value: string | null }) {
  return (
    <div className="flex items-center gap-3">
      <Icon size={15} className="text-text-muted flex-shrink-0" />
      <span className="text-xs text-text-secondary">{label}</span>
      <span className="flex-1 border-b border-dashed border-divider" />
      <span className="text-xs font-medium text-text-primary truncate max-w-[55%] text-right">{value || "—"}</span>
    </div>
  );
}

function checkinCell(status: string) {
  if (!status) return <span className="text-text-muted">—</span>;
  const color = status === "Early Arrival" ? "text-success" : status === "Late Arrival" ? "text-danger" : "text-info";
  return <span className={`font-medium ${color}`}>{status}</span>;
}

function checkoutCell(status: string) {
  if (!status) return <span className="text-text-muted">—</span>;
  const color =
    status === "Late Departure" ? "text-success"
    : status === "Early Departure" ? "text-danger"
    : status === "Incomplete" ? "text-text-secondary"
    : "text-info";
  return <span className={`font-medium ${color}`}>{status}</span>;
}

const ATTENDANCE_COLUMNS = [
  { key: "day_date", header: "Day / Date" },
  { key: "checkin_time", header: "Check-in" },
  { key: "checkin_status", header: "Check-in Status", cell: (r: any) => checkinCell(r.checkin_status) },
  { key: "checkout_time", header: "Check-out" },
  { key: "checkout_status", header: "Check-out Status", cell: (r: any) => checkoutCell(r.checkout_status) },
  {
    key: "attendance_status",
    header: "Attendance Status",
    cell: (r: any) =>
      r.attendance_status ? (
        <span className="font-medium text-success">{r.attendance_status}</span>
      ) : (
        <span className="text-text-muted">—</span>
      ),
  },
];

const LEAVE_COLUMNS = [
  { key: "start_date", header: "Start Date" },
  { key: "end_date", header: "End Date" },
  { key: "leave_type", header: "Leave Type" },
  {
    key: "status",
    header: "Status",
    cell: (r: any) =>
      r.status === "Current" ? (
        <span className="font-medium text-warning">Current</span>
      ) : (
        <span className="text-text-secondary">Taken</span>
      ),
  },
];

const TRAINING_COLUMNS = [
  { key: "venue", header: "Venue" },
  { key: "consultant", header: "Consultant" },
  { key: "location", header: "Location" },
  { key: "start_date", header: "Start Date" },
  { key: "end_date", header: "End Date" },
  { key: "title", header: "Title" },
];

const TABS: { key: TabKey; label: string }[] = [
  { key: "attendance", label: "Attendance" },
  { key: "leave", label: "Leave" },
  { key: "training", label: "Training" },
];

export default function EmployeeDetailSheet({ employeeId, onClose, defaultDateRange }: EmployeeDetailSheetProps) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<DateRange>(defaultDateRange || getDefaultDateRange());
  const [workingHours, setWorkingHours] = useState<any>(null);
  const [tab, setTab] = useState<TabKey>("attendance");
  const [tabStates, setTabStates] = useState<Record<TabKey, TabState>>({
    attendance: makeTabState("day_date"),
    leave: makeTabState("start_date"),
    training: makeTabState("start_date"),
  });

  // Body scroll lock + Escape handler
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  // Target thresholds for the graphs
  useEffect(() => {
    api.get("/api/rules").then((r) => setWorkingHours(r.data?.working_hours ?? null)).catch(() => {});
  }, []);

  const fetchData = useCallback(() => {
    if (!employeeId) return;
    setLoading(true);
    setError(null);
    api
      .get(`/api/employees/${employeeId}/attendance-stats`, {
        params: { start_date: dateRange.startDate, end_date: dateRange.endDate },
      })
      .then((r) => { setData(r.data); setLoading(false); })
      .catch((e) => { setError(e?.response?.data?.detail || "Failed to load"); setLoading(false); });
  }, [employeeId, dateRange.startDate, dateRange.endDate]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const updateTab = (key: TabKey, patch: Partial<TabState>) =>
    setTabStates((prev) => ({ ...prev, [key]: { ...prev[key], ...patch } }));

  // Debounce the search input for the active tab
  const activeSearchInput = tabStates[tab].searchInput;
  useEffect(() => {
    const id = window.setTimeout(() => {
      setTabStates((prev) => ({
        ...prev,
        [tab]: { ...prev[tab], search: prev[tab].searchInput, page: 1 },
      }));
    }, 350);
    return () => window.clearTimeout(id);
  }, [activeSearchInput, tab]);

  // Reset all tables to page 1 when the date range changes
  const handleDateChange = (range: DateRange) => {
    setDateRange(range);
    setTabStates((prev) => ({
      attendance: { ...prev.attendance, page: 1 },
      leave: { ...prev.leave, page: 1 },
      training: { ...prev.training, page: 1 },
    }));
  };

  const active = tabStates[tab];
  const filtersForApi = useMemo(() => {
    const out: Record<string, string[]> = {};
    for (const [k, set] of Object.entries(active.filters)) if (set.size > 0) out[k] = [...set];
    return out;
  }, [active.filters]);

  const { data: records, isLoading: recordsLoading, isFetching: recordsFetching } = useEmployeeRecords({
    idNo: employeeId,
    type: tab,
    startDate: dateRange.startDate,
    endDate: dateRange.endDate,
    page: active.page,
    pageSize: active.pageSize,
    search: active.search,
    sortBy: active.sorting[0]?.id ?? DEFAULT_SORT[tab],
    sortDir: active.sorting[0]?.desc ? "desc" : "asc",
    filters: filtersForApi,
  });

  const employee = data?.employee;
  const summary = data?.summary;
  const daily = data?.daily_attendance || [];

  const checkinThresholds = useMemo(() => {
    const dates = daily.filter((d: any) => d.checkin_time).map((d: any) => d.date);
    return resolveDayThresholds(workingHours, dates, "checkin");
  }, [workingHours, daily]);
  const checkoutThresholds = useMemo(() => {
    const dates = daily.filter((d: any) => d.checkout_time).map((d: any) => d.date);
    return resolveDayThresholds(workingHours, dates, "checkout");
  }, [workingHours, daily]);

  const checkinTargetMinutes = useMemo(
    () => (checkinThresholds?.normal_start ? parseTimeMinutes(checkinThresholds.normal_start) : null),
    [checkinThresholds]
  );
  const checkoutTargetMinutes = useMemo(
    () => (checkoutThresholds?.normal_start ? parseTimeMinutes(checkoutThresholds.normal_start) : null),
    [checkoutThresholds]
  );

  const weekdayShort = (dateStr: string) => {
    const d = new Date(dateStr + "T12:00:00");
    return ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][d.getDay()];
  };

  const checkinChartData = daily
    .filter((d: any) => d.checkin_time)
    .map((d: any) => {
      const minutes = parseTimeMinutes(d.checkin_time);
      return { label: `${weekdayShort(d.date)} ${d.date.slice(5)}`, minutes, color: colorForTime(minutes, checkinThresholds) };
    });
  const checkoutChartData = daily
    .filter((d: any) => d.checkout_time)
    .map((d: any) => {
      const minutes = parseTimeMinutes(d.checkout_time);
      let color = "#722ED1";
      if (checkoutThresholds) {
        const eb = checkoutThresholds.early_before ? parseTimeMinutes(checkoutThresholds.early_before) : null;
        const la = checkoutThresholds.late_after ? parseTimeMinutes(checkoutThresholds.late_after) : null;
        if (eb !== null && minutes < eb) color = "#FF4D4F";
        else if (la !== null && minutes > la) color = "#52C41A";
      }
      return { label: `${weekdayShort(d.date)} ${d.date.slice(5)}`, minutes, color };
    });

  const formatMinutes = (m: number) => {
    const h = Math.floor(m / 60), min = m % 60;
    const ampm = h >= 12 ? "PM" : "AM";
    return `${h % 12 || 12}:${String(min).padStart(2, "0")} ${ampm}`;
  };

  const initials = employee?.full_name?.split(" ").map((n: string) => n[0]).slice(0, 2).join("").toUpperCase() || "?";
  const isActive = Boolean(employee?.is_active);

  const metrics = [
    { label: "Total Present Days", value: summary?.present ?? 0 },
    { label: "Total Absent Days", value: summary?.absent ?? 0 },
    { label: "Total Leave Days", value: summary?.leave ?? 0 },
    { label: "Total Training Days", value: summary?.training ?? 0 },
  ];

  const tableColumns = tab === "attendance" ? ATTENDANCE_COLUMNS : tab === "leave" ? LEAVE_COLUMNS : TRAINING_COLUMNS;

  const modal = (
    <AnimatePresence mode="wait">
      <div className="fixed inset-0 z-50">
        <motion.div
          className="absolute inset-0 bg-black/40"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onClick={onClose}
        />
        <motion.div
          className="absolute left-0 right-0 bottom-0 bg-surface border-t border-border shadow-2xl overflow-hidden flex flex-col rounded-t-xl"
          style={{ height: "85vh" }}
          initial={{ y: "100%" }}
          animate={{ y: 0 }}
          exit={{ y: "100%" }}
          transition={{ type: "spring", damping: 30, stiffness: 300 }}
        >
          {/* Drag handle */}
          <div className="flex justify-center pt-2.5 pb-1 flex-shrink-0">
            <div className="w-10 h-1 rounded-full bg-border" />
          </div>

          {/* Header */}
          <div className="flex items-center justify-between px-5 h-[56px] border-b border-divider flex-shrink-0">
            <h2 className="text-[12px] font-semibold tracking-wide text-text-primary uppercase">
              Employee Attendance Details
            </h2>
            <button
              onClick={onClose}
              aria-label="Close"
              className="w-6 h-6 flex items-center justify-center text-text-secondary hover:text-text-primary rounded hover:bg-nav-hover transition-colors"
            >
              <X size={16} />
            </button>
          </div>

          {loading ? (
            <div className="flex-1 flex items-center justify-center text-text-muted text-sm">Loading...</div>
          ) : error ? (
            <div className="flex-1 flex items-center justify-center text-danger text-sm">{error}</div>
          ) : (
            <div className="flex-1 overflow-y-auto">
              {/* Employee information */}
              <div className="p-5 grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="rounded-card bg-canvas border border-border p-4 flex items-center gap-4">
                  <div className="relative flex-shrink-0">
                    <div className="w-14 h-14 rounded-full bg-accent text-white flex items-center justify-center font-semibold text-lg">
                      {initials}
                    </div>
                    <span
                      className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full border-2 border-white"
                      style={{ backgroundColor: isActive ? "#52C41A" : "#8C8C8C" }}
                    />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-[16px] font-semibold text-text-primary truncate">{employee?.full_name || "—"}</h3>
                      <span
                        className={`inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full ${
                          isActive ? "bg-badge-green-bg text-badge-green-text" : "bg-nav-hover text-text-secondary"
                        }`}
                      >
                        {isActive && <Check size={11} />}
                        {employee?.status || "—"}
                      </span>
                    </div>
                    <p className="text-xs text-text-muted mt-1">ID: {employee?.id_no}</p>
                  </div>
                </div>

                <div className="rounded-card border border-border p-4 space-y-3">
                  <AttrRow icon={Building2} label="Department" value={employee?.department} />
                  <AttrRow icon={User} label="Role" value={employee?.rank} />
                  <AttrRow icon={Briefcase} label="Employment" value={employee?.employment_type} />
                  <AttrRow icon={Clock} label="Avg. Work Hours" value={data?.avg_work_hours} />
                </div>
              </div>

              {/* Attendance Summary */}
              <div className="px-5 pb-5">
                <h4 className="text-[14px] font-semibold text-text-primary mb-3">Attendance Summary</h4>
                <div className="rounded-card border border-border grid grid-cols-2 sm:grid-cols-4 divide-x divide-divider">
                  {metrics.map((m) => (
                    <div key={m.label} className="p-4 text-center">
                      <p className="text-xs text-text-secondary">{m.label}</p>
                      <p className="text-xl font-bold text-text-primary mt-1.5">{m.value}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Graphs */}
              <div className="px-5 pb-5 grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="rounded-card border border-border p-4">
                  <h4 className="text-xs font-semibold text-text-primary mb-1">Check-in Times</h4>
                  {checkinTargetMinutes !== null && (
                    <p className="text-[11px] text-text-muted mb-2">
                      Target: {formatMinutes(checkinTargetMinutes)} ·{" "}
                      <span style={{ color: "#52C41A" }}>Early</span> / <span style={{ color: "#1677FF" }}>Normal</span> /{" "}
                      <span style={{ color: "#FF4D4F" }}>Late</span>
                    </p>
                  )}
                  {checkinChartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={180}>
                      <LineChart data={checkinChartData} margin={{ left: 0, right: 10, top: 4, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                        <XAxis dataKey="label" tick={{ fontSize: 10, fill: "#94A3B8" }} interval="preserveStartEnd" />
                        <YAxis ticks={FULL_DAY_TICKS} tick={{ fontSize: 10, fill: "#94A3B8" }} tickFormatter={formatMinutes} domain={[0, 1440]} />
                        <Tooltip formatter={(v: number) => formatMinutes(v)} contentStyle={{ borderRadius: 8, border: "1px solid #EAECF0", fontSize: 12 }} />
                        {checkinTargetMinutes !== null && (
                          <ReferenceLine y={checkinTargetMinutes} stroke="#FAAD14" strokeDasharray="6 3" />
                        )}
                        <Line type="monotone" dataKey="minutes" stroke="#1677FF" strokeWidth={2} dot={(props: any) => {
                          const { cx, cy, payload } = props;
                          return <circle key={`${payload.label}-${payload.minutes}`} cx={cx} cy={cy} r={4} fill={payload.color} stroke="#fff" strokeWidth={1} />;
                        }} />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="text-xs text-text-muted text-center py-8">No check-in data</p>
                  )}
                </div>

                <div className="rounded-card border border-border p-4">
                  <h4 className="text-xs font-semibold text-text-primary mb-1">Check-out Times</h4>
                  {checkoutTargetMinutes !== null && (
                    <p className="text-[11px] text-text-muted mb-2">
                      Target: {formatMinutes(checkoutTargetMinutes)} ·{" "}
                      <span style={{ color: "#722ED1" }}>Normal</span> / <span style={{ color: "#52C41A" }}>Late</span> /{" "}
                      <span style={{ color: "#FF4D4F" }}>Early</span>
                    </p>
                  )}
                  {checkoutChartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={180}>
                      <LineChart data={checkoutChartData} margin={{ left: 0, right: 10, top: 4, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                        <XAxis dataKey="label" tick={{ fontSize: 10, fill: "#94A3B8" }} interval="preserveStartEnd" />
                        <YAxis ticks={FULL_DAY_TICKS} tick={{ fontSize: 10, fill: "#94A3B8" }} tickFormatter={formatMinutes} domain={[0, 1440]} />
                        <Tooltip formatter={(v: number) => formatMinutes(v)} contentStyle={{ borderRadius: 8, border: "1px solid #EAECF0", fontSize: 12 }} />
                        {checkoutTargetMinutes !== null && (
                          <ReferenceLine y={checkoutTargetMinutes} stroke="#FAAD14" strokeDasharray="6 3" />
                        )}
                        <Line type="monotone" dataKey="minutes" stroke="#722ED1" strokeWidth={2} dot={(props: any) => {
                          const { cx, cy, payload } = props;
                          return <circle key={`${payload.label}-${payload.minutes}`} cx={cx} cy={cy} r={4} fill={payload.color} stroke="#fff" strokeWidth={1} />;
                        }} />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="text-xs text-text-muted text-center py-8">No check-out data</p>
                  )}
                </div>
              </div>

              {/* Segmented control + date selector + table */}
              <div className="px-5 pb-6">
                <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
                  <div className="flex items-center gap-1 bg-nav-hover rounded-btn p-0.5">
                    {TABS.map((t) => (
                      <button
                        key={t.key}
                        onClick={() => setTab(t.key)}
                        className={`px-3 py-1 text-xs font-medium rounded-[5px] transition-all ${
                          tab === t.key ? "bg-surface text-accent shadow-sm" : "text-text-secondary hover:text-text-primary"
                        }`}
                      >
                        {t.label}
                      </button>
                    ))}
                  </div>
                  <DateRangePicker value={dateRange} onChange={handleDateChange} />
                </div>

                <DataTable
                  title={tab === "attendance" ? "Attendance" : tab === "leave" ? "Leave" : "Training"}
                  columns={tableColumns as any}
                  data={records?.items || []}
                  loading={recordsLoading}
                  isFetching={recordsFetching}
                  searchable
                  enableColumnFilters
                  serverSide
                  total={records?.total ?? 0}
                  page={active.page}
                  pageSize={active.pageSize}
                  pageSizeOptions={[10, 25, 50]}
                  onPageChange={(p) => updateTab(tab, { page: p })}
                  onPageSizeChange={(n) => updateTab(tab, { pageSize: n, page: 1 })}
                  sorting={active.sorting}
                  onSortingChange={(s) => updateTab(tab, { sorting: s, page: 1 })}
                  search={active.searchInput}
                  onSearchChange={(s) => updateTab(tab, { searchInput: s })}
                  columnFilters={active.filters}
                  onColumnFiltersChange={(f) => updateTab(tab, { filters: f, page: 1 })}
                  filterOptions={records?.filter_options || {}}
                />
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </AnimatePresence>
  );

  if (typeof document !== "undefined") {
    return createPortal(modal, document.body);
  }
  return modal;
}
