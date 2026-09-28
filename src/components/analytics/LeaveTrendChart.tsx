import RangeTrendChart from "@/components/analytics/RangeTrendChart";

interface LeaveTrendChartProps {
  /** Global scope filters (record-table filters do not apply). */
  filters: Record<string, string[]>;
  /** Chart range seeds from this once, then lives independently. */
  initialRange: { start: string; end: string } | null;
}

/** Staff on leave over time: distinct staff overlapping each bucket, one series per department. */
export default function LeaveTrendChart({ filters, initialRange }: LeaveTrendChartProps) {
  return (
    <RangeTrendChart
      domain="leave"
      title="Staff on Leave Over Time"
      staffNoun="staff with leave"
      spanNoun="leave"
      staffField="staff_on_leave"
      exportName="leave_trend"
      filters={filters}
      initialRange={initialRange}
    />
  );
}
