import { useEffect, useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import DateRangePicker, { getDefaultDateRange } from "@/components/ui/DateRangePicker";
import type { DateRange } from "@/components/ui/DateRangePicker";
import { useClickableLegend } from "@/lib/chartUtils";
import { distinctColor } from "@/lib/analyticsColors";
import { fmtDateShort, fmtDateMonth } from "@/lib/format";
import ExportMenu from "@/components/analytics/ExportMenu";
import { useRangeTrend } from "@/hooks/useAnalytics";

interface RangeTrendChartProps {
  domain: "leave" | "training";
  title: string;
  /** e.g. "staff with leave" / "staff in training" (subtitle + tooltip context). */
  staffNoun: string;
  /** e.g. "leave" / "training" (empty state). */
  spanNoun: string;
  /** CSV column for the staff count. */
  staffField: string;
  /** CSV file prefix. */
  exportName: string;
  /** Global scope filters (record-table filters do not apply). */
  filters: Record<string, string[]>;
  /** Chart range seeds from this once, then lives independently. */
  initialRange: { start: string; end: string } | null;
}

/** Staff-over-time chart: distinct staff overlapping each bucket, one series per department. */
export default function RangeTrendChart({
  domain,
  title,
  staffNoun,
  spanNoun,
  staffField,
  exportName,
  filters,
  initialRange,
}: RangeTrendChartProps) {
  const [trendRange, setTrendRange] = useState<DateRange>(() =>
    initialRange
      ? {
          startDate: initialRange.start,
          endDate: initialRange.end,
          label: `${fmtDateShort(initialRange.start)} – ${fmtDateShort(initialRange.end)}`,
        }
      : getDefaultDateRange()
  );

  // Global range broadcasts into the chart picker (dashboard behavior):
  // the picker shows the global range; manual edits diverge until the
  // next global change.
  useEffect(() => {
    if (!initialRange?.start || !initialRange?.end) return;
    setTrendRange({
      startDate: initialRange.start,
      endDate: initialRange.end,
      label: `${fmtDateShort(initialRange.start)} – ${fmtDateShort(initialRange.end)}`,
    });
  }, [initialRange?.start, initialRange?.end]);

  // Intelligent grouping: multiple calendar months → monthly buckets,
  // a single month → daily buckets.
  const granularity = useMemo(() => {
    const [sy, sm] = trendRange.startDate.split("-").map(Number);
    const [ey, em] = trendRange.endDate.split("-").map(Number);
    return sy === ey && sm === em ? "day" : "month";
  }, [trendRange]);

  const trend = useRangeTrend(domain, {
    start: trendRange.startDate,
    end: trendRange.endDate,
    granularity,
    filters,
  });

  const { isHidden, toggle } = useClickableLegend();

  const departments = useMemo(() => {
    const set = new Set((trend.data?.rows || []).map((r) => r.department));
    return [...set].sort((a, b) => a.localeCompare(b));
  }, [trend.data]);

  const colorOf = (dept: string) => distinctColor(departments.indexOf(dept));

  const chartData = useMemo(() => {
    const byBucket = new Map<string, Record<string, unknown>>();
    for (const r of trend.data?.rows || []) {
      let row = byBucket.get(r.bucket);
      if (!row) {
        row = {
          bucket: r.bucket,
          label: granularity === "month" ? fmtDateMonth(r.bucket) : fmtDateShort(r.bucket),
        };
        byBucket.set(r.bucket, row);
      }
      row[r.department] = r.staff;
    }
    return [...byBucket.values()];
  }, [trend.data, granularity]);

  const visibleDepts = departments.filter((d) => !isHidden(d));

  const handleLegendClick = (entry: any) => {
    if (departments.includes(entry.value)) toggle(entry.value);
  };

  const subtitle = `Distinct ${staffNoun} overlapping each ${
    granularity === "month" ? "month" : "day"
  } click legend to toggle departments`;

  if (trend.isLoading) {
    return (
      <div className="card-container p-5 animate-pulse">
        <div className="flex justify-between mb-4">
          <div className="h-5 w-48 bg-nav-hover rounded" />
          <div className="h-8 w-28 bg-nav-hover rounded-btn" />
        </div>
        <div className="h-[300px] bg-nav-hover rounded-lg" />
      </div>
    );
  }

  return (
    <div className="card-container p-5 flex flex-col">
      <div className="flex items-center justify-between mb-2 flex-wrap gap-2 flex-shrink-0">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
          <p className="text-xs text-text-secondary mt-0.5">{subtitle}</p>
        </div>
        <div className="flex items-center gap-2">
          <ExportMenu
            getRows={() =>
              (trend.data?.rows || []).map((r) => ({
                bucket: r.bucket,
                department: r.department,
                [staffField]: r.staff,
              }))
            }
            fileName={exportName}
            dateRange={{ startDate: trendRange.startDate, endDate: trendRange.endDate }}
          />
          <DateRangePicker value={trendRange} onChange={setTrendRange} />
        </div>
      </div>

      {chartData.length === 0 ? (
        <div className="flex flex-col items-center justify-center text-text-muted gap-2 py-16">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" opacity={0.4}>
            <path d="M3 3v18h18" /><path d="M7 15l4-6 4 3 4-7" />
          </svg>
          <p className="text-sm font-medium">No {spanNoun} in this range</p>
          <p className="text-xs">Try selecting a different date range</p>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#EAECF0" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: "#EAECF0" }}
              minTickGap={24}
            />
            <YAxis
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{
                borderRadius: 8,
                border: "1px solid #EAECF0",
                boxShadow: "0px 4px 12px rgba(0,0,0,0.06)",
                fontSize: 12,
              }}
              formatter={(value: number, name: string) => [`${value} staff`, name]}
            />
            <Legend
              onClick={handleLegendClick}
              payload={departments.map((d) => ({
                value: d,
                color: isHidden(d) ? "#CBD5E1" : colorOf(d),
                type: "line" as const,
              }))}
              formatter={(value: string) => (
                <span className={isHidden(value) ? "opacity-40" : ""} style={{ color: "#64748B", fontSize: 12 }}>
                  {value}
                </span>
              )}
              wrapperStyle={{ cursor: "pointer" }}
            />
            {visibleDepts.map((d) => (
              <Line
                key={d}
                type="monotone"
                dataKey={d}
                stroke={colorOf(d)}
                strokeWidth={2}
                dot={false}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
