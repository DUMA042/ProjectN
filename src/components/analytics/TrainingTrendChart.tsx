import RangeTrendChart from "@/components/analytics/RangeTrendChart";

interface TrainingTrendChartProps {
  /** Global scope filters (record-table filters do not apply). */
  filters: Record<string, string[]>;
  /** Chart range seeds from this once, then lives independently. */
  initialRange: { start: string; end: string } | null;
}

/** Staff in training over time: distinct staff overlapping each bucket, one series per department. */
export default function TrainingTrendChart({ filters, initialRange }: TrainingTrendChartProps) {
  return (
    <RangeTrendChart
      domain="training"
      title="Staff in Training Over Time"
      staffNoun="staff in training"
      spanNoun="training"
      staffField="staff_in_training"
      exportName="training_trend"
      filters={filters}
      initialRange={initialRange}
    />
  );
}
