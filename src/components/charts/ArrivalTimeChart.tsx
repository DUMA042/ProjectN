import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import DateRangePicker from "@/components/ui/DateRangePicker";
import { useClickableLegend } from "@/lib/chartUtils";
import type { DateRange } from "@/components/ui/DateRangePicker";

const SERIES = [
  { key: "early_arrival", label: "Early Arrival", color: "#10B981" },
  { key: "normal_arrival", label: "Normal Arrival", color: "#3B82F6" },
  { key: "late_arrival", label: "Late Arrival", color: "#EF4444" },
  { key: "early_departure", label: "Early Departure", color: "#F59E0B" },
  { key: "normal_departure", label: "Normal Departure", color: "#6366F1" },
  { key: "late_departure", label: "Late Departure", color: "#8B5CF6" },
  { key: "incomplete", label: "Incomplete", color: "#64748B" },
];

interface ArrivalTimeChartProps {
  title: string;
  data: Record<string, any>[];
  dateRange: DateRange;
  onDateChange: (range: DateRange) => void;
  selectedDepartment?: string;
  onDepartmentChange?: (dept: string) => void;
  departments?: string[];
  loading?: boolean;
}

export default function ArrivalTimeChart({
  title,
  data,
  dateRange,
  onDateChange,
  selectedDepartment = "",
  onDepartmentChange,
  departments = [],
  loading,
}: ArrivalTimeChartProps) {
  const { isHidden, toggle } = useClickableLegend();

  if (loading) {
    return (
      <div className="card-container p-5 animate-pulse h-[440px]">
        <div className="flex justify-between mb-4">
          <div className="h-5 w-48 bg-nav-hover rounded" />
          <div className="flex gap-2">
            <div className="h-8 w-32 bg-nav-hover rounded-btn" />
            <div className="h-8 w-28 bg-nav-hover rounded-btn" />
          </div>
        </div>
        <div className="h-[360px] bg-nav-hover rounded-lg" />
      </div>
    );
  }

  const chartData = (data || []).map((d) => ({
    name: String(d.category_label ?? "").length > 14
      ? String(d.category_label).slice(0, 14) + "…"
      : String(d.category_label ?? ""),
    fullName: String(d.category_label ?? ""),
    early_arrival: d.early_arrival ?? 0,
    normal_arrival: d.normal_arrival ?? 0,
    late_arrival: d.late_arrival ?? 0,
    early_departure: d.early_departure ?? 0,
    normal_departure: d.normal_departure ?? 0,
    late_departure: d.late_departure ?? 0,
    incomplete: d.incomplete ?? 0,
  }));

  const handleLegendClick = (entry: any) => {
    const s = SERIES.find((item) => item.label === entry.value);
    if (s) toggle(s.key);
  };

  const isByGrade = Boolean(
    selectedDepartment &&
      selectedDepartment.toLowerCase() !== "all department" &&
      selectedDepartment.toLowerCase() !== "all departments"
  );

  if (!loading && (!data || data.length === 0)) {
    return (
      <div className="card-container p-5 h-[440px] flex flex-col">
        <div className="flex items-center justify-between mb-2 flex-wrap gap-2 flex-shrink-0">
          <div>
            <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
            <p className="text-xs text-text-secondary mt-0.5">No data for selected period</p>
          </div>
          <div className="flex items-center gap-2">
            {onDepartmentChange && (
              <select
                value={selectedDepartment}
                onChange={(e) => onDepartmentChange(e.target.value)}
                className="px-3 py-1.5 text-xs border border-border rounded-btn bg-surface text-text-secondary cursor-pointer hover:bg-nav-hover transition-colors font-medium"
              >
                <option value="">All department</option>
                {departments.map((dept) => (
                  <option key={dept} value={dept}>{dept}</option>
                ))}
              </select>
            )}
            <DateRangePicker value={dateRange} onChange={onDateChange} />
          </div>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center text-text-muted gap-2">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" opacity={0.4}>
            <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>
          </svg>
          <p className="text-sm font-medium">No arrival time records</p>
          <p className="text-xs">Try selecting a different date range or location</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card-container p-5 h-[440px] flex flex-col justify-between">
      <div className="flex items-center justify-between mb-2 flex-wrap gap-2 flex-shrink-0">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
          <p className="text-xs text-text-secondary mt-0.5">
            {isByGrade
              ? `Breakdown by Grade Level (${selectedDepartment})`
              : "Breakdown by Department"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {onDepartmentChange && (
            <select
              value={selectedDepartment}
              onChange={(e) => onDepartmentChange(e.target.value)}
              className="px-3 py-1.5 text-xs border border-border rounded-btn bg-surface text-text-secondary cursor-pointer hover:bg-nav-hover transition-colors font-medium"
            >
              <option value="">All department</option>
              {departments.map((dept) => (
                <option key={dept} value={dept}>
                  {dept}
                </option>
              ))}
            </select>
          )}
          <DateRangePicker value={dateRange} onChange={onDateChange} />
        </div>
      </div>

      <div className="flex-1 min-h-0 pt-2">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ left: -15, right: 10, top: 10, bottom: 45 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10, fill: "#64748B" }}
              interval={0}
              angle={-35}
              textAnchor="end"
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "#94A3B8" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                borderRadius: 8,
                border: "1px solid #EAECF0",
                boxShadow: "0px 4px 12px rgba(0,0,0,0.06)",
              }}
              formatter={(value: number, name: string) => [value.toLocaleString(), name]}
              labelFormatter={(label, payload) => payload?.[0]?.payload?.fullName || label}
            />
            <Legend
              onClick={handleLegendClick}
              iconType="square"
              iconSize={10}
              payload={SERIES.map((s) => ({ value: s.label, color: isHidden(s.key) ? "#CBD5E1" : s.color, type: "square" as const }))}
              wrapperStyle={{ cursor: "pointer", paddingTop: 16 }}
              formatter={(value: string) => {
                const sKey = SERIES.find((s) => s.label === value)?.key || value;
                return (
                  <span className={isHidden(sKey) ? "opacity-40" : ""} style={{ color: "#64748B", fontSize: 11, fontWeight: 500 }}
                  >
                    {value}
                  </span>
                );
              }}
            />
            {SERIES.map((s) => (
              <Bar
                key={s.key}
                dataKey={s.key}
                name={s.label}
                fill={isHidden(s.key) ? "transparent" : s.color}
                radius={[3, 3, 0, 0]}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
