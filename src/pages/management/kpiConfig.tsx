import { useScopedTotals } from "@/hooks/useAnalytics";
import { useAnalyticsSignals } from "@/hooks/useAnalytics";
import { fmtNum, fmtPct, fmtDelta } from "@/lib/format";

/** Shared scope-totals config — used by both NarrativeHeader and PulseTab so
 * react-query serves both from one request. */
export const PULSE_TOTAL_DOMAINS = [
  { domain: "employees" as const, metrics: ["employees", "active"] },
  {
    domain: "attendance" as const,
    metrics: ["attendance_rate", "absence_rate", "coverage", "present_days", "absent_days", "late_arrivals"],
  },
  { domain: "leave" as const, metrics: ["leave_records", "unique_staff"] },
  { domain: "training" as const, metrics: ["activities", "participants"] },
];

interface NarrativeHeaderProps {
  filters: Record<string, string[]>;
  dateRange: { start: string; end: string } | null;
  compare: boolean;
}

/** Auto-generated one-line story of the current scope. */
export default function NarrativeHeader({ filters, dateRange, compare }: NarrativeHeaderProps) {
  const totals = useScopedTotals(PULSE_TOTAL_DOMAINS, filters, dateRange, compare);
  const signals = useAnalyticsSignals(dateRange, filters);

  const [empQ, attQ, leaveQ] = totals;
  const emp = empQ.data?.totals || {};
  const att = attQ.data?.totals || {};
  const leave = leaveQ.data?.totals || {};
  const pAtt = attQ.data?.previous_totals || {};
  const loading = totals.some((q) => q.isLoading) || signals.isLoading;

  const flagged = (signals.data?.signals || []).filter((s) => s.severity !== "info");
  const flagText =
    flagged.length === 0
      ? null
      : flagged.length === 1
        ? `${flagged[0].segment} flagged`
        : `${flagged.length} areas flagged`;

  const rate = att.attendance_rate;
  const rateDelta =
    compare && pAtt.attendance_rate != null && rate != null
      ? Math.round((Number(rate) - Number(pAtt.attendance_rate)) * 10) / 10
      : null;

  const parts: { text: string; strong?: boolean; tone?: "good" | "bad" }[] = [
    { text: "Attendance ", strong: false },
    { text: fmtPct(rate ?? null), strong: true },
    ...(rateDelta != null
      ? [{ text: ` (${fmtDelta(rateDelta, "pp")})`, strong: false, tone: rateDelta >= 0 ? ("good" as const) : ("bad" as const) }]
      : []),
    { text: " · headcount ", strong: false },
    { text: fmtNum(emp.employees ?? null), strong: true },
    { text: " · on leave ", strong: false },
    { text: fmtNum(leave.unique_staff ?? null), strong: true },
    ...(flagText ? [{ text: " · ", strong: false }, { text: flagText, strong: true, tone: "bad" as const }] : []),
  ];

  if (loading) {
    return <div className="h-5 w-2/3 max-w-xl bg-nav-hover rounded animate-pulse" />;
  }
  if (rate == null && !emp.employees) {
    return (
      <p className="text-xs text-text-muted">
        No data in scope — adjust the date range or filters, or click Refresh to rebuild the analytics table.
      </p>
    );
  }

  return (
    <p className="text-[13px] text-text-secondary flex items-center flex-wrap gap-x-1">
      {parts.map((p, i) => (
        <span
          key={i}
          className={
            p.strong
              ? `font-semibold tabular-nums ${p.tone === "bad" ? "text-danger" : p.tone === "good" ? "text-badge-green-text" : "text-text-primary"}`
              : p.tone === "bad"
                ? "text-danger"
                : p.tone === "good"
                  ? "text-badge-green-text"
                  : ""
          }
        >
          {p.text}
        </span>
      ))}
    </p>
  );
}
