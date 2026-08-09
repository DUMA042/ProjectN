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

const SEGMENTS = [
  { key: "attendance_pct", label: "Attendance", color: "#10B981" },
  { key: "absent_pct", label: "Absent", color: "#EF4444" },
  { key: "leave_pct", label: "Leave", color: "#F59E0B" },
  { key: "training_pct", label: "Training", color: "#6366F1" },
];

interface DeptAttendanceChartProps {
  title: string;
  data: Record<string, any>[];
  dateRange: DateRange;
  onDateChange: (range: DateRange) => void;
  location?: string;
  loading?: boolean;
}

export default function DeptAttendanceChart({
  title,
  data,
  dateRange,
  onDateChange,
  location = "HQ",
  loading,
}: DeptAttendanceChartProps) {
  const { isHidden, toggle } = useClickableLegend();

  if (loading) {
    return (
      <div className="card-container p-5 animate-pulse h-[440px]">
        <div className="flex justify-between mb-4">
          <div className="h-5 w-48 bg-nav-hover rounded" />
          <div className="h-8 w-28 bg-nav-hover rounded-btn" />
        </div>
        <div className="h-[360px] bg-nav-hover rounded-lg" />
      </div>
    );
  }

  const chartData = (data || []).map((d) => ({
    name: d.department_name?.length > 14
      ? d.department_name.slice(0, 14) + "…"
      : d.department_name,
    fullName: d.department_name,
    attendance_pct: d.attendance_pct ?? 0,
    absent_pct: d.absent_pct ?? 0,
    leave_pct: d.leave_pct ?? 0,
    training_pct: d.training_pct ?? 0,
    total: d.total_staff,
  }));

  const handleLegendClick = (entry: any) => {
    const seg = SEGMENTS.find((s) => s.label === entry.value);
    if (seg) toggle(seg.key);
  };

  return (
    <div className="card-container p-5 h-[440px] flex flex-col justify-between">
      <div className="flex items-center justify-between mb-2 flex-shrink-0">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
          <p className="text-xs text-text-secondary mt-0.5">Clustered breakdown for all {location} departments</p>
        </div>
        <DateRangePicker value={dateRange} onChange={onDateChange} />
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
              unit="%"
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{ borderRadius: 8, border: "1px solid #EAECF0", boxShadow: "0px 4px 12px rgba(0,0,0,0.06)" }}
              formatter={(value: number, name: string) => [`${value}%`, name]}
              labelFormatter={(label, payload) => payload?.[0]?.payload?.fullName || label}
            />
            <Legend
              onClick={handleLegendClick}
              iconType="square"
              iconSize={10}
              payload={SEGMENTS.map((s) => ({ value: s.label, color: isHidden(s.key) ? "#CBD5E1" : s.color, type: "square" as const }))}
              wrapperStyle={{ cursor: "pointer", paddingTop: 16 }}
            formatter={(value: string) => {
              const segKey = SEGMENTS.find(s => s.label === value)?.key || value;
              return (
                <span className={isHidden(segKey) ? "opacity-40" : ""} style={{ color: "#64748B", fontSize: 12 }}>
                  {value}
                </span>
              );
            }}
            />
            {SEGMENTS.map((seg) => (
              <Bar
                key={seg.key}
                dataKey={seg.key}
                name={seg.label}
                fill={isHidden(seg.key) ? "transparent" : seg.color}
                radius={[3, 3, 0, 0]}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
