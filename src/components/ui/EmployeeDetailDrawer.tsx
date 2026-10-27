import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { X, Clock, Umbrella, GraduationCap, CalendarDays, Pencil } from "lucide-react";
import { api } from "@/lib/api";
import CalendarHeatmap from "@/components/ui/CalendarHeatmap";
import EmployeeEditForm from "@/components/ui/EmployeeEditForm";
import { useToast } from "@/components/ui/Toast";
import { useEmployeeLookups, useEmployeeUpdate } from "@/hooks/useEmployee";
import { fmtPct } from "@/lib/format";
import type { EmployeeDetail } from "@/lib/staff";

interface AttendanceStats {
  summary: { present?: number; absent?: number; leave?: number; training?: number };
  avg_work_hours: string | null;
  daily_attendance: { date: string; status: string; checkin_time: string | null; checkout_time: string | null }[];
}

const DRAWER_DAYS = 90;

function isoDaysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function useEmployeeDetail(idNo: string | null) {
  return useQuery({
    queryKey: ["employee-detail", idNo],
    queryFn: () => api.get(`/api/employees/${idNo}/detail`).then((r) => r.data as EmployeeDetail),
    enabled: !!idNo,
  });
}

function useEmployeeAttendance(idNo: string | null) {
  return useQuery({
    queryKey: ["employee-attendance-90d", idNo],
    queryFn: () =>
      api
        .get(`/api/employees/${idNo}/attendance-stats`, {
          params: { start_date: isoDaysAgo(DRAWER_DAYS - 1), end_date: isoDaysAgo(0) },
        })
        .then((r) => r.data as AttendanceStats),
    enabled: !!idNo,
  });
}

function useDepartmentRate(department: string | null, idNo: string | null) {
  return useQuery({
    queryKey: ["employee-dept-rate", department, idNo],
    queryFn: () =>
      api
        .post("/api/analytics/explore", {
          domain: "attendance",
          metrics: ["attendance_rate"],
          group_by: ["department"],
          filters: department ? { department: [department] } : {},
          date_range: { start: isoDaysAgo(DRAWER_DAYS - 1), end: isoDaysAgo(0) },
          page: 1,
          page_size: 5,
        })
        .then((r) => r.data as { groups?: Record<string, unknown>[] }),
    enabled: !!idNo && !!department,
  });
}

/** Monthly attendance % from daily statuses (present / working days elapsed). */
function monthlySeries(days: { date: string; status: string }[]): { label: string; pct: number }[] {
  const buckets = new Map<string, { present: number; working: number }>();
  days.forEach((d) => {
    if (!["present", "absent", "late"].includes(d.status)) return;
    const m = d.date.slice(0, 7);
    const b = buckets.get(m) || { present: 0, working: 0 };
    b.working += 1;
    if (d.status === "present") b.present += 1;
    buckets.set(m, b);
  });
  return [...buckets.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-6)
    .map(([m, b]) => ({
      label: new Date(`${m}-01T00:00:00`).toLocaleDateString("en-GB", { month: "short" }),
      pct: b.working > 0 ? Math.round((100 * b.present) / b.working) : 0,
    }));
}

interface EmployeeDetailDrawerProps {
  employeeId: string | null;
  onClose: () => void;
}

function saveErrorMessage(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data
    ?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "message" in detail) {
    return String((detail as { message: unknown }).message);
  }
  return "Could not save changes. Please try again.";
}

export default function EmployeeDetailDrawer({ employeeId, onClose }: EmployeeDetailDrawerProps) {
  const { data: detail, isLoading } = useEmployeeDetail(employeeId);
  const { data: att } = useEmployeeAttendance(employeeId);
  const { data: deptQ } = useDepartmentRate(detail?.department || null, employeeId);
  const [editing, setEditing] = useState(false);
  const { toast } = useToast();
  const lookups = useEmployeeLookups(Boolean(editing && employeeId));
  const update = useEmployeeUpdate(employeeId);

  useEffect(() => {
    setEditing(false);
    update.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [employeeId]);

  const months = att ? monthlySeries(att.daily_attendance || []) : [];
  const empRate = att && att.summary ? att.summary : null;
  const deptRate = deptQ?.groups?.find((g) => g.department === detail?.department)?.attendance_rate;

  const empRatePct = empRate
    ? (() => {
        const working = (empRate.present || 0) + (empRate.absent || 0);
        return working > 0 ? Math.round((100 * (empRate.present || 0)) / working) : null;
      })()
    : null;

  return (
    <AnimatePresence>
      {employeeId && (
        <>
          <motion.div
            className="fixed inset-0 bg-black/20 z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            className="fixed right-0 top-0 h-full w-[520px] max-w-[92vw] bg-surface border-l border-border z-50 flex flex-col"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 26, stiffness: 220 }}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-divider flex-shrink-0">
              <h3 className="text-sm font-semibold text-text-primary">Employee Detail</h3>
              <div className="flex items-center gap-1">
                {detail && !editing && (
                  <button
                    onClick={() => setEditing(true)}
                    aria-label="Edit employee"
                    title="Edit employee"
                    className="p-1.5 rounded-btn hover:bg-nav-hover text-text-muted hover:text-text-secondary"
                  >
                    <Pencil size={16} />
                  </button>
                )}
                <button onClick={onClose} className="p-1.5 rounded-btn hover:bg-nav-hover text-text-muted hover:text-text-secondary">
                  <X size={18} />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              {isLoading ? (
                <div className="space-y-3 animate-pulse">
                  {[...Array(8)].map((_, i) => (
                    <div key={i} className="h-5 bg-nav-hover rounded" />
                  ))}
                </div>
              ) : editing && detail ? (
                lookups.isLoading ? (
                  <p className="text-sm text-text-muted">Loading options…</p>
                ) : lookups.data ? (
                  <EmployeeEditForm
                    employee={detail}
                    lookups={lookups.data}
                    saving={update.isPending}
                    error={update.error ? saveErrorMessage(update.error) : null}
                    onCancel={() => {
                      setEditing(false);
                      update.reset();
                    }}
                    onSave={(changes) =>
                      update.mutate(changes, {
                        onSuccess: () => {
                          setEditing(false);
                          toast("Employee details updated", "success");
                        },
                      })
                    }
                  />
                ) : (
                  <p className="text-sm text-danger">Could not load edit options.</p>
                )
              ) : detail ? (
                <>
                  <div>
                    <h4 className="text-base font-semibold text-text-primary">{detail.full_name}</h4>
                    <p className="text-sm text-text-secondary">{detail.id_no}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-sm">
                    {[
                      ["Department", detail.department],
                      ["Rank", detail.rank],
                      ["Grade Level", detail.grade_level],
                      ["Status", detail.status],
                      ["Employment Type", detail.employment_type],
                      ["Sex", detail.sex],
                      ["Geo Zone", detail.geographical_zone],
                      ["Phone", detail.phone_number || "—"],
                      ["Last Deployment", detail.date_of_last_deployment || "—"],
                      ["Avg Work Hours", att?.avg_work_hours || "—"],
                    ].map(([label, value]) => (
                      <div key={label}>
                        <p className="text-xs text-text-muted">{label}</p>
                        <p className="text-text-primary font-medium">{value}</p>
                      </div>
                    ))}
                  </div>

                  {/* 90-day calendar */}
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <CalendarDays size={14} className="text-accent" />
                      <p className="text-xs font-semibold text-text-secondary uppercase">Last {DRAWER_DAYS} days</p>
                    </div>
                    <CalendarHeatmap
                      days={(att?.daily_attendance || []).map((d) => ({ date: d.date, status: d.status }))}
                      cell={12}
                    />
                  </div>

                  {/* monthly attendance + vs department */}
                  {months.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-text-secondary uppercase mb-2">Monthly attendance</p>
                      <div className="flex items-end gap-3">
                        {months.map((m) => (
                          <div key={m.label} className="flex flex-col items-center gap-1">
                            <span className="text-[10px] font-semibold text-text-secondary tabular-nums">{m.pct}%</span>
                            <div className="w-6 rounded-t-[3px] bg-accent/80" style={{ height: Math.max(4, (m.pct / 100) * 56) }} />
                            <span className="text-[10px] text-text-muted">{m.label}</span>
                          </div>
                        ))}
                        {empRatePct != null && deptRate != null && (
                          <div className="ml-auto self-center text-right">
                            <p className="text-sm font-semibold text-text-primary tabular-nums">{fmtPct(empRatePct, 0)}</p>
                            <p className="text-[11px] text-text-muted">
                              vs department{" "}
                              <span className={`font-semibold ${Number(deptRate) > empRatePct ? "text-warning" : "text-badge-green-text"}`}>
                                {fmtPct(Number(deptRate), 0)}
                              </span>
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {detail.remark && (
                    <div>
                      <p className="text-xs text-text-muted mb-1">Remark</p>
                      <p className="text-sm text-text-secondary bg-nav-hover rounded-input p-2">{detail.remark}</p>
                    </div>
                  )}

                  {detail.card_swipes.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <Clock size={14} className="text-accent" />
                        <p className="text-xs font-semibold text-text-secondary uppercase">Recent Swipes</p>
                      </div>
                      <div className="space-y-1">
                        {detail.card_swipes.slice(0, 10).map((s) => (
                          <div key={s.swipe_id} className="flex justify-between text-xs py-1.5 px-2 rounded hover:bg-nav-hover">
                            <span className="text-text-secondary">{s.location}</span>
                            <span className="text-text-primary font-mono">
                              {s.swipe_time ? new Date(s.swipe_time).toLocaleString("en-GB") : "—"}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {detail.leave_records.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <Umbrella size={14} className="text-warning" />
                        <p className="text-xs font-semibold text-text-secondary uppercase">Recent Leave</p>
                      </div>
                      <div className="space-y-1">
                        {detail.leave_records.slice(0, 10).map((l) => (
                          <div key={l.record_id} className="flex justify-between text-xs py-1.5 px-2 rounded hover:bg-nav-hover">
                            <span className="text-text-secondary">{l.leave_type_name}</span>
                            <span className="text-text-primary font-mono">{l.start_date} – {l.end_date}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {detail.training_records.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <GraduationCap size={14} className="text-info" />
                        <p className="text-xs font-semibold text-text-secondary uppercase">Recent Training</p>
                      </div>
                      <div className="space-y-1">
                        {detail.training_records.slice(0, 10).map((t) => (
                          <div key={t.training_id} className="text-xs py-1.5 px-2 rounded hover:bg-nav-hover">
                            <p className="text-text-primary font-medium">{t.title || "Training"}</p>
                            <p className="text-text-muted">{t.venue} · {t.consultant} · {t.start_date}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-sm text-text-muted">Employee not found</p>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
