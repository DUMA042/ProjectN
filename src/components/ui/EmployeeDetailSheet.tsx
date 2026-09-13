import { useState, useEffect, useCallback, useMemo } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { X, User, Phone, MapPin, Briefcase, Shield, TrendingUp, Calendar, Award } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { api } from "@/lib/api";
import DateRangePicker from "@/components/ui/DateRangePicker";
import { getDefaultDateRange } from "@/components/ui/DateRangePicker";
import type { DateRange } from "@/components/ui/DateRangePicker";

interface EmployeeDetailSheetProps {
  employeeId: string;
  onClose: () => void;
  defaultDateRange?: DateRange;
}

const STATUS_COLORS: Record<string, string> = {
  present: "#52C41A",
  leave: "#FAAD14",
  absent: "#FF4D4F",
  training: "#1677FF",
  inactive: "#BFBFBF",
  weekend: "transparent",
  holiday: "#FFF7E6",
  upcoming: "#F5F5F5",
};

const STATUS_BG: Record<string, string> = {
  present: "#F0FDF4",
  leave: "#FFFBE6",
  absent: "#FFF2F0",
  training: "#F0F5FF",
  inactive: "#F5F5F5",
  upcoming: "#F5F5F5",
};

// Full 24h Y-axis ticks every 4 hours
const FULL_DAY_TICKS = [0, 240, 480, 720, 960, 1200, 1440];

function parseTimeMinutes(s: string): number {
  const [h, m] = s.split(":").map(String).join(":").split(":").map(Number);
  return (h || 0) * 60 + (m || 0);
}

// Resolve day-name for a date string
function dayNameOf(dateStr: string): string {
  const d = new Date(dateStr + "T12:00:00");
  return ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"][d.getDay()];
}

// Pick target + thresholds for a set of working dates
function resolveDayThresholds(workingHours: any, dates: string[], kind: "checkin" | "checkout") {
  if (!workingHours) return null;
  // Prefer the most common weekday in the range; fallback to first available
  for (const ds of dates) {
    const dn = dayNameOf(ds);
    const wh = workingHours[dn];
    if (wh && wh[kind]) return wh[kind];
  }
  // Fallback: first non-null day in working_hours
  for (const dn of ["monday", "tuesday", "wednesday", "thursday", "friday"]) {
    const wh = workingHours[dn];
    if (wh && wh[kind]) return wh[kind];
  }
  return null;
}

function colorForTime(minutes: number, thresholds: any): string {
  if (!thresholds) return thresholds === null ? "#1677FF" : "#1677FF";
  const earlyBefore = thresholds.early_before ? parseTimeMinutes(thresholds.early_before) : null;
  const lateAfter = thresholds.late_after ? parseTimeMinutes(thresholds.late_after) : null;
  if (earlyBefore !== null && minutes < earlyBefore) return "#52C41A"; // early
  if (lateAfter !== null && minutes > lateAfter) return "#FF4D4F"; // late
  return "#1677FF"; // normal
}

type HeatmapDay = { day: string; status: string; date: string } | null;
type HeatmapWeek = HeatmapDay[];

const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] as const;

function buildHeatmapWeeks(daily: { date: string; status: string }[]): HeatmapWeek[] {
  if (!daily.length) return [];
  const byDate = new Map(daily.map((d) => [d.date, d.status]));
  const startDate = new Date(daily[0].date + "T00:00:00");
  const endDate = new Date(daily[daily.length - 1].date + "T00:00:00");
  const weeks: HeatmapWeek[] = [];
  let currentWeek: HeatmapWeek = [null, null, null, null, null, null, null]; // Mon..Sun slots
  const current = new Date(startDate);
  while (current <= endDate) {
    const wd = (current.getDay() + 6) % 7; // Mon=0 ... Sun=6
    // Local date key (must match backend's local date strings, not UTC)
    const dateStr = `${current.getFullYear()}-${String(current.getMonth() + 1).padStart(2, "0")}-${String(current.getDate()).padStart(2, "0")}`;
    let status = byDate.get(dateStr) || "absent";
    // Never render weekends/holidays as absent
    if (wd >= 5) status = "weekend";
    currentWeek[wd] = { day: DAY_NAMES[wd], status, date: dateStr };
    if (wd === 6 || current.getTime() === endDate.getTime()) {
      weeks.push(currentWeek);
      currentWeek = [null, null, null, null, null, null, null];
    }
    current.setDate(current.getDate() + 1);
  }
  if (currentWeek.some(Boolean)) weeks.push(currentWeek);
  return weeks;
}

function heatmapCellStyle(status: string): React.CSSProperties {
  if (status === "weekend") {
    return { backgroundColor: "transparent", border: "1px solid #EAECF0", opacity: 1 };
  }
  if (status === "holiday") {
    return { backgroundColor: "#FFF7E6", border: "1px solid #FFD666", opacity: 1 };
  }
  if (status === "upcoming") {
    return { backgroundColor: "#F5F5F5", border: "1px solid #EAECF0", opacity: 1 };
  }
  if (status === "inactive") {
    return { backgroundColor: STATUS_COLORS.inactive, opacity: 0.6 };
  }
  return { backgroundColor: STATUS_COLORS[status] || "#F0F0F0", opacity: 0.85 };
}

function ProfileTile({ icon: Icon, label, value }: { icon: any; label: string; value: string | null }) {
  return (
    <div className="flex items-center gap-2 p-2 rounded-btn bg-nav-hover">
      <Icon size={14} className="text-accent flex-shrink-0" />
      <div className="min-w-0">
        <p className="text-[10px] text-text-muted leading-tight">{label}</p>
        <p className="text-xs font-medium text-text-primary truncate">{value || "—"}</p>
      </div>
    </div>
  );
}

export default function EmployeeDetailSheet({ employeeId, onClose, defaultDateRange }: EmployeeDetailSheetProps) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<DateRange>(defaultDateRange || getDefaultDateRange());
  const [workingHours, setWorkingHours] = useState<any>(null);

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

  // Fetch target thresholds from rules (non-blocking — chart still renders without them)
  useEffect(() => {
    api.get("/api/rules").then((r) => {
      setWorkingHours(r.data?.working_hours ?? null);
    }).catch(() => {});
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

  const employee = data?.employee;
  const summary = data?.summary;
  const daily = data?.daily_attendance || [];
  const heatmapWeeks = buildHeatmapWeeks(daily);

  // Enrich chart data with weekday label + computed color
  const checkinThresholds = useMemo(() => {
    const dates = daily.filter((d: any) => d.checkin_time).map((d: any) => d.date);
    return resolveDayThresholds(workingHours, dates, "checkin");
  }, [workingHours, daily]);
  const checkoutThresholds = useMemo(() => {
    const dates = daily.filter((d: any) => d.checkout_time).map((d: any) => d.date);
    return resolveDayThresholds(workingHours, dates, "checkout");
  }, [workingHours, daily]);

  const checkinTargetMinutes = useMemo(() => {
    if (!checkinThresholds?.normal_start) return null;
    return parseTimeMinutes(checkinThresholds.normal_start);
  }, [checkinThresholds]);
  const checkoutTargetMinutes = useMemo(() => {
    if (!checkoutThresholds?.normal_start) return null;
    return parseTimeMinutes(checkoutThresholds.normal_start);
  }, [checkoutThresholds]);

  const weekdayShort = (dateStr: string) => {
    const d = new Date(dateStr + "T12:00:00");
    return ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][d.getDay()];
  };

  const checkinChartData = daily
    .filter((d: any) => d.checkin_time)
    .map((d: any) => {
      const [h, m] = d.checkin_time.split(":").map(Number);
      const minutes = h * 60 + m;
      return {
        label: `${weekdayShort(d.date)} ${d.date.slice(5)}`,
        minutes,
        color: colorForTime(minutes, checkinThresholds),
      };
    });
  const checkoutChartData = daily
    .filter((d: any) => d.checkout_time)
    .map((d: any) => {
      const [h, m] = d.checkout_time.split(":").map(Number);
      const minutes = h * 60 + m;
      // Checkout early is bad (red), late is good (green) — mirror checkin logic for late_after
      let color = "#722ED1";
      if (checkoutThresholds) {
        const earlyBefore = checkoutThresholds.early_before ? parseTimeMinutes(checkoutThresholds.early_before) : null;
        const lateAfter = checkoutThresholds.late_after ? parseTimeMinutes(checkoutThresholds.late_after) : null;
        if (earlyBefore !== null && minutes < earlyBefore) color = "#FF4D4F";
        else if (lateAfter !== null && minutes > lateAfter) color = "#52C41A";
        else color = "#722ED1";
      }
      return { label: `${weekdayShort(d.date)} ${d.date.slice(5)}`, minutes, color };
    });

  const formatMinutes = (m: number) => {
    const h = Math.floor(m / 60), min = m % 60;
    const ampm = h >= 12 ? "PM" : "AM";
    return `${h % 12 || 12}:${String(min).padStart(2, "0")} ${ampm}`;
  };

  const initials = employee?.full_name?.split(" ").map((n: string) => n[0]).slice(0, 2).join("").toUpperCase() || "?";

  const summaryCards = [
    { label: "Present", count: summary?.present ?? 0, color: STATUS_COLORS.present, bg: STATUS_BG.present },
    { label: "Absent", count: summary?.absent ?? 0, color: STATUS_COLORS.absent, bg: STATUS_BG.absent },
    { label: "Leave", count: summary?.leave ?? 0, color: STATUS_COLORS.leave, bg: STATUS_BG.leave },
    { label: "Training", count: summary?.training ?? 0, color: STATUS_COLORS.training, bg: STATUS_BG.training },
  ];

  const sheet = (
    <AnimatePresence mode="wait">
      <div className="fixed inset-0 z-50">
        <motion.div
          className="absolute inset-0 bg-black/40"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onClick={onClose}
        />
        <motion.div
          className="absolute left-0 right-0 bottom-0 bg-surface rounded-t-xl shadow-2xl overflow-hidden"
          style={{ maxHeight: "85vh" }}
          initial={{ y: "100%" }} animate={{ y: 0 }} exit={{ y: "100%" }}
          transition={{ type: "spring", damping: 30, stiffness: 300 }}
        >
          <div className="flex justify-center pt-3 pb-1">
            <div className="w-10 h-1 rounded-full bg-border" />
          </div>

          <div className="flex items-center justify-between px-6 pb-4 border-b border-divider flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-full bg-accent flex items-center justify-center text-white font-semibold text-sm">
                {initials}
              </div>
              <div>
                <h2 className="text-base font-semibold text-text-primary">{employee?.full_name || "—"}</h2>
                <p className="text-xs text-text-secondary">ID: {employee?.id_no} · {employee?.department} · {employee?.grade_level}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <DateRangePicker value={dateRange} onChange={setDateRange} />
              <button onClick={onClose} aria-label="Close" className="p-2 rounded-btn text-text-muted hover:text-text-primary hover:bg-nav-hover transition-colors">
                <X size={18} />
              </button>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center h-40 text-text-muted text-sm">Loading...</div>
          ) : error ? (
            <div className="flex items-center justify-center h-40 text-danger text-sm">{error}</div>
          ) : (
            <div className="overflow-y-auto" style={{ maxHeight: "calc(85vh - 80px)" }}>
              <div className="p-6 space-y-5">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <ProfileTile icon={User} label="Sex" value={employee?.sex} />
                  <ProfileTile icon={Phone} label="Phone" value={employee?.phone_number} />
                  <ProfileTile icon={Briefcase} label="Department" value={employee?.department} />
                  <ProfileTile icon={Award} label="Grade" value={employee?.grade_level} />
                  <ProfileTile icon={Shield} label="Rank" value={employee?.rank} />
                  <ProfileTile icon={TrendingUp} label="Status" value={employee?.status} />
                  <ProfileTile icon={Calendar} label="Emp. Type" value={employee?.employment_type} />
                  <ProfileTile icon={MapPin} label="Zone" value={employee?.geographical_zone} />
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {summaryCards.map((s) => (
                    <div key={s.label} className="rounded-card border border-border p-3 text-center" style={{ backgroundColor: s.bg }}>
                      <p className="text-lg font-bold" style={{ color: s.color }}>{s.count}</p>
                      <p className="text-xs text-text-secondary mt-0.5">{s.label}</p>
                    </div>
                  ))}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <div className="rounded-card border border-border p-4">
                    <h4 className="text-xs font-semibold text-text-primary mb-1">Check-in Times</h4>
                    {checkinTargetMinutes !== null && (
                      <p className="text-[11px] text-text-muted mb-2">Target: {formatMinutes(checkinTargetMinutes)} · <span style={{ color: "#52C41A" }}>Early</span> / <span style={{ color: "#1677FF" }}>Normal</span> / <span style={{ color: "#FF4D4F" }}>Late</span></p>
                    )}
                    {checkinChartData.length > 0 ? (
                      <ResponsiveContainer width="100%" height={200}>
                        <LineChart data={checkinChartData} margin={{ left: 0, right: 10, top: 4, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                          <XAxis dataKey="label" tick={{ fontSize: 10, fill: "#94A3B8" }} interval="preserveStartEnd" />
                          <YAxis ticks={FULL_DAY_TICKS} tick={{ fontSize: 10, fill: "#94A3B8" }} tickFormatter={formatMinutes} domain={[0, 1440]} />
                          <Tooltip formatter={(v: number) => formatMinutes(v)} labelFormatter={(l) => String(l)} contentStyle={{ borderRadius: 8, border: "1px solid #EAECF0", fontSize: 12 }} />
                          {checkinTargetMinutes !== null && (
                            <ReferenceLine y={checkinTargetMinutes} stroke="#FAAD14" strokeDasharray="6 3" label={{ value: `Target ${formatMinutes(checkinTargetMinutes)}`, fill: "#8C6D1F", fontSize: 10, position: "insideTopRight" }} />
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
                      <p className="text-[11px] text-text-muted mb-2">Target: {formatMinutes(checkoutTargetMinutes)} · <span style={{ color: "#722ED1" }}>Normal</span> / <span style={{ color: "#52C41A" }}>Late</span> / <span style={{ color: "#FF4D4F" }}>Early</span></p>
                    )}
                    {checkoutChartData.length > 0 ? (
                      <ResponsiveContainer width="100%" height={200}>
                        <LineChart data={checkoutChartData} margin={{ left: 0, right: 10, top: 4, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                          <XAxis dataKey="label" tick={{ fontSize: 10, fill: "#94A3B8" }} interval="preserveStartEnd" />
                          <YAxis ticks={FULL_DAY_TICKS} tick={{ fontSize: 10, fill: "#94A3B8" }} tickFormatter={formatMinutes} domain={[0, 1440]} />
                          <Tooltip formatter={(v: number) => formatMinutes(v)} labelFormatter={(l) => String(l)} contentStyle={{ borderRadius: 8, border: "1px solid #EAECF0", fontSize: 12 }} />
                          {checkoutTargetMinutes !== null && (
                            <ReferenceLine y={checkoutTargetMinutes} stroke="#FAAD14" strokeDasharray="6 3" label={{ value: `Target ${formatMinutes(checkoutTargetMinutes)}`, fill: "#8C6D1F", fontSize: 10, position: "insideTopRight" }} />
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

                <div className="rounded-card border border-border p-4">
                  <h4 className="text-xs font-semibold text-text-primary mb-3">Activity Heatmap</h4>
                  {heatmapWeeks.length > 0 ? (
                    <div className="overflow-x-auto">
                      {/* Weekday headers */}
                      <div className="flex gap-1 mb-1">
                        {["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"].map((wd) => (
                          <div key={wd} className="w-[18px] text-center text-[9px] font-medium text-text-muted">{wd}</div>
                        ))}
                      </div>
                      <div className="flex flex-col gap-1">
                        {heatmapWeeks.map((week, wi) => (
                          <div key={wi} className="flex gap-1">
                            {week.map((day, di) =>
                              day ? (
                                <div key={di} title={`${day.date}: ${day.status}`} className="w-[18px] h-[18px] rounded-[3px] transition-colors" style={heatmapCellStyle(day.status)} />
                              ) : (
                                <div key={di} className="w-[18px] h-[18px]" />
                              )
                            )}
                          </div>
                        ))}
                      </div>
                      <div className="flex items-center gap-3 mt-3 pt-2 border-t border-divider flex-wrap">
                        {Object.entries(STATUS_COLORS).filter(([k]) => !["inactive", "weekend", "holiday", "upcoming"].includes(k)).map(([k, c]) => (
                          <div key={k} className="flex items-center gap-1">
                            <div className="w-2.5 h-2.5 rounded-[2px]" style={{ backgroundColor: c as string }} />
                            <span className="text-[10px] text-text-muted capitalize">{k}</span>
                          </div>
                        ))}
                        <div className="flex items-center gap-1">
                          <div className="w-2.5 h-2.5 rounded-[2px] border border-border" style={{ backgroundColor: "transparent" }} />
                          <span className="text-[10px] text-text-muted">Weekend</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <div className="w-2.5 h-2.5 rounded-[2px] border" style={{ backgroundColor: "#FFF7E6", borderColor: "#FFD666" }} />
                          <span className="text-[10px] text-text-muted">Holiday</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <div className="w-2.5 h-2.5 rounded-[2px]" style={{ backgroundColor: "#BFBFBF" }} />
                          <span className="text-[10px] text-text-muted">Inactive</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <div className="w-2.5 h-2.5 rounded-[2px] border border-border" style={{ backgroundColor: "#F5F5F5" }} />
                          <span className="text-[10px] text-text-muted">Upcoming</span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-text-muted text-center py-6">No activity data for this range</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </AnimatePresence>
  );

  // Portal to body so fixed positioning isn't clipped by page's overflow
  if (typeof document !== "undefined") {
    return createPortal(sheet, document.body);
  }
  return sheet;
}
