import { useMemo } from "react";
import KpiStrip from "@/components/analytics/KpiStrip";
import type { Kpi } from "@/components/analytics/KpiStrip";
import CompositionChart from "@/components/analytics/CompositionChart";
import AttentionFlags from "@/components/analytics/AttentionFlags";
import type { AttentionFlag } from "@/components/analytics/AttentionFlags";
import { useAnalyticsExplore, useScopedTotals } from "@/hooks/useAnalytics";

interface OverviewTabProps {
  filters: Record<string, string[]>;
  dateRange: { start: string; end: string } | null;
  compare: boolean;
  onDrill: (dimension: string, value: string) => void;
  onGoToTab: (tab: string) => void;
}

function delta(cur: any, prev: any): number | null {
  if (cur == null || prev == null) return null;
  const d = Number(cur) - Number(prev);
  return Number.isFinite(d) ? Math.round(d * 10) / 10 : null;
}

export default function OverviewTab({ filters, dateRange, compare, onDrill, onGoToTab }: OverviewTabProps) {
  const totals = useScopedTotals(
    [
      { domain: "employees", metrics: ["employees", "active"] },
      { domain: "attendance", metrics: ["attendance_rate", "absence_rate", "coverage", "present_days", "absent_days"] },
      { domain: "leave", metrics: ["leave_records", "unique_staff"] },
      { domain: "training", metrics: ["activities", "participants"] },
    ],
    filters,
    dateRange,
    compare
  );
  const [empQ, attQ, leaveQ, trainQ] = totals;

  const emp = empQ.data?.totals || {};
  const att = attQ.data?.totals || {};
  const leave = leaveQ.data?.totals || {};
  const train = trainQ.data?.totals || {};
  const pEmp = empQ.data?.previous_totals || {};
  const pAtt = attQ.data?.previous_totals || {};
  const pLeave = leaveQ.data?.previous_totals || {};
  const pTrain = trainQ.data?.previous_totals || {};

  const kpis: Kpi[] = useMemo(
    () => [
      { label: "Employees", value: emp.employees ?? 0, delta: compare ? delta(emp.employees, pEmp.employees) : null },
      { label: "Active", value: emp.active ?? 0, delta: compare ? delta(emp.active, pEmp.active) : null },
      { label: "Attendance Rate", value: `${att.attendance_rate ?? 0}%`, delta: compare ? delta(att.attendance_rate, pAtt.attendance_rate) : null },
      { label: "Absence Rate", value: `${att.absence_rate ?? 0}%`, delta: compare ? delta(att.absence_rate, pAtt.absence_rate) : null },
      { label: "Coverage", value: `${att.coverage ?? 0}%`, sub: "staff with swipe data" },
      { label: "On Leave", value: leave.leave_records ?? 0, sub: `${leave.unique_staff ?? 0} staff`, delta: compare ? delta(leave.leave_records, pLeave.leave_records) : null },
      { label: "Training", value: train.activities ?? 0, sub: `${train.participants ?? 0} participants`, delta: compare ? delta(train.activities, pTrain.activities) : null },
    ],
    [emp, att, leave, train, pEmp, pAtt, pLeave, pTrain, compare]
  );

  const loading = totals.some((q) => q.isLoading);

  // Composition (employees by dimension)
  const byDept = useAnalyticsExplore({ domain: "employees", group_by: ["department"], metrics: ["employees"], filters, page_size: 100, sort_by: "employees", sort_dir: "desc" });
  const byGrade = useAnalyticsExplore({ domain: "employees", group_by: ["grade_level"], metrics: ["employees"], filters, page_size: 100, sort_by: "employees", sort_dir: "desc" });
  const byStatus = useAnalyticsExplore({ domain: "employees", group_by: ["status"], metrics: ["employees"], filters, page_size: 100, sort_by: "employees", sort_dir: "desc" });
  const bySex = useAnalyticsExplore({ domain: "employees", group_by: ["sex"], metrics: ["employees"], filters, page_size: 100, sort_by: "employees", sort_dir: "desc" });
  const byType = useAnalyticsExplore({ domain: "employees", group_by: ["employment_type"], metrics: ["employees"], filters, page_size: 100, sort_by: "employees", sort_dir: "desc" });

  // Attendance by department (for attention flags)
  const attByDept = useAnalyticsExplore({
    domain: "attendance", group_by: ["department"], metrics: ["attendance_rate", "absent_days", "coverage"],
    filters, date_range: dateRange, page_size: 100, sort_by: "attendance_rate", sort_dir: "asc",
  });

  const toData = (q: any, dim: string) =>
    (q.data?.groups || []).map((g: any) => ({ name: String(g[dim] ?? "—"), value: Number(g.employees ?? 0) }));

  const flags: AttentionFlag[] = useMemo(() => {
    const rows: any[] = attByDept.data?.groups || [];
    const out: AttentionFlag[] = [];
    rows.slice(0, 3).forEach((r) => {
      out.push({
        label: r.department,
        detail: `${r.attendance_rate ?? 0}% attendance · ${r.absent_days ?? 0} absent days`,
        tone: Number(r.attendance_rate ?? 0) < 15 ? "danger" : "warning",
        onClick: () => { onDrill("department", String(r.department)); onGoToTab("attendance"); },
      });
    });
    if (att.coverage != null && Number(att.coverage) < 50) {
      out.push({
        label: "Low swipe-data coverage",
        detail: `Only ${att.coverage}% of employees in scope have swipe data`,
        tone: "info",
      });
    }
    return out;
  }, [attByDept.data, att.coverage, onDrill, onGoToTab]);

  return (
    <div className="space-y-4">
      <KpiStrip items={kpis} loading={loading} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <CompositionChart title="Headcount by Department" data={toData(byDept, "department")} onSelect={(n) => onDrill("department", n)} loading={byDept.isLoading} />
        <CompositionChart title="Headcount by Grade Level" data={toData(byGrade, "grade_level")} onSelect={(n) => onDrill("grade_level", n)} loading={byGrade.isLoading} color="#52C41A" />
        <CompositionChart title="Headcount by Status" data={toData(byStatus, "status")} type="donut" onSelect={(n) => onDrill("status", n)} loading={byStatus.isLoading} />
        <CompositionChart title="Headcount by Sex" data={toData(bySex, "sex")} type="donut" onSelect={(n) => onDrill("sex", n)} loading={bySex.isLoading} />
        <CompositionChart title="Headcount by Employment Type" data={toData(byType, "employment_type")} onSelect={(n) => onDrill("employment_type", n)} loading={byType.isLoading} color="#722ED1" />
        <AttentionFlags flags={flags} loading={attByDept.isLoading} />
      </div>
    </div>
  );
}
