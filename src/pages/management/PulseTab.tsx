import { useMemo } from "react";
import StaggerReveal, { RevealItem } from "@/components/analytics/StaggerReveal";
import KpiStrip from "@/components/analytics/KpiStrip";
import type { Kpi } from "@/components/analytics/KpiStrip";
import TodayCard from "@/components/analytics/TodayCard";
import SignalFeed from "@/components/analytics/SignalFeed";
import DataHealthCard from "@/components/analytics/DataHealthCard";
import AttentionFlags from "@/components/analytics/AttentionFlags";
import type { AttentionFlag } from "@/components/analytics/AttentionFlags";
import TrendChart from "@/components/analytics/TrendChart";
import type { TrendPoint } from "@/components/analytics/TrendChart";
import { useAnalyticsExplore, useAnalyticsSignals, useScopedTotals, useAnalyticsMetrics } from "@/hooks/useAnalytics";
import { useManagementScope } from "@/hooks/useManagementScope";
import { semanticColor } from "@/lib/analyticsColors";
import { PULSE_TOTAL_DOMAINS } from "./kpiConfig";
import { useTabExport } from "./exportRegistry";
import { exportToCSV } from "@/lib/csvExport";
import { fmtDateShort } from "@/lib/format";

interface PulseTabProps {
  filters: Record<string, string[]>;
  dateRange: { start: string; end: string } | null;
  compare: boolean;
  onDrill: (dimension: string, value: string) => void;
  onGoToTab: (tab: string) => void;
  onOpenEmployee: (id: string) => void;
}

function isoDay(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function weekStart(dstr: string): string {
  const d = new Date(dstr.length === 10 ? `${dstr}T00:00:00` : dstr);
  const dow = (d.getDay() + 6) % 7;
  d.setDate(d.getDate() - dow);
  return isoDay(d);
}

/** Roll daily points into week-start buckets (mean of available days).
 * Returns the chart points plus a label→week-start map for drill-through. */
function toWeekly(points: { label: string; value: number }[]): {
  points: TrendPoint[];
  weekOf: Map<string, string>;
} {
  const buckets = new Map<string, { sum: number; n: number }>();
  points.forEach((p) => {
    const wk = weekStart(p.label);
    const b = buckets.get(wk) || { sum: 0, n: 0 };
    b.sum += p.value;
    b.n += 1;
    buckets.set(wk, b);
  });
  const weekOf = new Map<string, string>();
  const out = [...buckets.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([wk, b]) => {
      const label = fmtDateShort(wk);
      weekOf.set(label, wk);
      return { label, value: Math.round((b.sum / b.n) * 10) / 10 };
    });
  return { points: out, weekOf };
}

export default function PulseTab({ filters, dateRange, compare, onDrill, onGoToTab, onOpenEmployee }: PulseTabProps) {
  const totals = useScopedTotals(PULSE_TOTAL_DOMAINS, filters, dateRange, compare);
  const { data: metricData } = useAnalyticsMetrics();
  const { setDateRange } = useManagementScope();
  const [empQ, attQ, leaveQ, trainQ] = totals;
  const emp = empQ.data?.totals || {};
  const att = attQ.data?.totals || {};
  const leave = leaveQ.data?.totals || {};
  const train = trainQ.data?.totals || {};
  const pEmp = empQ.data?.previous_totals || {};
  const pAtt = attQ.data?.previous_totals || {};
  const pLeave = leaveQ.data?.previous_totals || {};
  const pTrain = trainQ.data?.previous_totals || {};

  const signals = useAnalyticsSignals(dateRange, filters);
  const signalList = signals.data?.signals || [];

  const delta = (cur: unknown, prev: unknown): number | null => {
    if (cur == null || prev == null) return null;
    const d = Number(cur) - Number(prev);
    return Number.isFinite(d) ? Math.round(d * 10) / 10 : null;
  };

  const kpis: Kpi[] = useMemo(
    () => {
      const metaOf = (key: string) => (metricData?.metrics || []).find((m) => m.key === key);
      // Semantic ring color for fixed-pivot (percentage) metrics: blue above
      // the good/bad line, red below it. Others keep the accent.
      const ringColor = (key: string, value: unknown): string | undefined => {
        const meta = metaOf(key);
        if (!meta || meta.pivot == null || value == null || !Number.isFinite(Number(value))) return undefined;
        return semanticColor(Number(value), meta, meta.pivot, 40);
      };
      return [
      { label: "Attendance Rate", value: att.attendance_rate ?? 0, ring: att.attendance_rate ?? 0, color: ringColor("attendance_rate", att.attendance_rate), delta: compare ? delta(att.attendance_rate, pAtt.attendance_rate) : null, polarity: "up_good" },
      { label: "Absence Rate", value: att.absence_rate ?? 0, delta: compare ? delta(att.absence_rate, pAtt.absence_rate) : null, polarity: "up_bad" },
      { label: "Coverage", value: att.coverage ?? 0, ring: att.coverage ?? 0, color: ringColor("coverage", att.coverage), sub: "staff with swipe data", polarity: "up_good" },
      { label: "Present Days", value: att.present_days ?? 0, delta: compare ? delta(att.present_days, pAtt.present_days) : null, polarity: "up_good" },
      { label: "Absent Days", value: att.absent_days ?? 0, delta: compare ? delta(att.absent_days, pAtt.absent_days) : null, polarity: "up_bad" },
      { label: "Late Arrivals", value: att.late_arrivals ?? 0, delta: compare ? delta(att.late_arrivals, pAtt.late_arrivals) : null, polarity: "up_bad" },
      { label: "Staff on Leave", value: leave.unique_staff ?? 0, sub: `${leave.leave_records ?? 0} records`, delta: compare ? delta(leave.unique_staff, pLeave.unique_staff) : null, polarity: "up_bad" },
      { label: "In Training", value: train.participants ?? 0, sub: `${train.activities ?? 0} activities`, delta: compare ? delta(train.participants, pTrain.participants) : null },
      ];
    },
    [emp, att, leave, train, pEmp, pAtt, pLeave, pTrain, compare, metricData] // eslint-disable-line react-hooks/exhaustive-deps
  );

  // 12-week context trend (rolled client-side from day granularity)
  const dailyTrend = useAnalyticsExplore({
    domain: "attendance", group_by: ["day"], metrics: ["attendance_rate"],
    filters, date_range: dateRange, sort_by: "day", sort_dir: "asc", page_size: 500,
  });
  const prevDr = useMemo(() => {
    if (!dateRange) return null;
    const s = new Date(`${dateRange.start}T00:00:00`);
    const e = new Date(`${dateRange.end}T00:00:00`);
    const len = Math.round((e.getTime() - s.getTime()) / 86_400_000) + 1;
    const pe = new Date(s); pe.setDate(s.getDate() - 1);
    const ps = new Date(pe); ps.setDate(pe.getDate() - (len - 1));
    return { start: isoDay(ps), end: isoDay(pe) };
  }, [dateRange]);
  const dailyPrev = useAnalyticsExplore({
    domain: "attendance", group_by: ["day"], metrics: ["attendance_rate"],
    filters, date_range: prevDr, sort_by: "day", sort_dir: "asc", page_size: 500,
    enabled: compare && !!prevDr,
  });

  const weekly = useMemo(
    () => toWeekly((dailyTrend.data?.groups || []).map((g: Record<string, unknown>) => ({
      label: String(g.day || ""), value: Number(g.attendance_rate ?? 0),
    }))),
    [dailyTrend.data]
  );
  const weeklyPrev = compare
    ? toWeekly((dailyPrev.data?.groups || []).map((g: Record<string, unknown>) => ({
        label: String(g.day || ""), value: Number(g.attendance_rate ?? 0),
      }))).points
    : undefined;

  // Employee threshold signals → Attention card
  const attention: AttentionFlag[] = signalList
    .filter((s) => s.drill.dimension === "employee_id")
    .slice(0, 5)
    .map((s) => ({
      label: s.segment,
      detail: s.headline,
      tone: s.severity === "danger" ? "danger" : s.severity === "warning" ? "warning" : "info",
      onClick: () => onOpenEmployee(String(s.drill.value)),
    }));

  useTabExport(
    signalList.length > 0
      ? () =>
          exportToCSV(
            signalList.map((s) => ({
              severity: s.severity,
              segment: s.segment,
              dimension: s.dimension,
              metric: s.metric_label,
              current: s.current,
              previous: s.previous,
              change: s.delta_pp ?? s.pct_change,
            })),
            "pulse_signals",
            dateRange ? { startDate: dateRange.start, endDate: dateRange.end } : undefined
          )
      : null
  );

  return (
    <StaggerReveal className="space-y-4">
      <RevealItem>
        <KpiStrip items={kpis} loading={totals.some((q) => q.isLoading)} />
      </RevealItem>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.7fr] gap-4">
        <RevealItem>
          <TodayCard filters={filters} />
        </RevealItem>
        <RevealItem>
          <SignalFeed
            signals={signalList}
            loading={signals.isLoading}
            onDrill={(dim, value) => { onDrill(dim, value); onGoToTab("trends"); }}
            onOpenEmployee={onOpenEmployee}
          />
        </RevealItem>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <RevealItem>
          <DataHealthCard health={signals.data?.health} loading={signals.isLoading} />
        </RevealItem>
        <RevealItem>
          <TrendChart
            title="Attendance rate · weekly"
            subtitle="Average attendance per week in the selected range — click a week to investigate it in Trends"
            data={weekly.points}
            compareData={weeklyPrev}
            suffix="%"
            height={190}
            onPointClick={(label) => {
              const ws = weekly.weekOf.get(label);
              if (!ws) return;
              const end = new Date(`${ws}T00:00:00`);
              end.setDate(end.getDate() + 6);
              setDateRange({ startDate: ws, endDate: isoDay(end), label: `Week of ${fmtDateShort(ws)}` });
              onGoToTab("trends");
            }}
          />
        </RevealItem>
        <RevealItem>
          <AttentionFlags flags={attention} loading={signals.isLoading} />
        </RevealItem>
      </div>
    </StaggerReveal>
  );
}
