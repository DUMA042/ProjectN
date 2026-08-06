import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Cell,
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
  loading?: boolean;
}

export default function DeptAttendanceChart({
  title,
  data,
  dateRange,
  onDateChange,
  loading,
}: DeptAttendanceChartProps) {
  const { isHidden, toggle } = useClickableLegend();

  if (loading) {
    return (
      <div className="card-container p-5 animate-pulse">
        <div className="flex justify-between mb-4">
          <div className="h-5 w-48 bg-nav-hover rounded" />
          <div className="h-8 w-28 bg-nav-hover rounded-btn" />
        </div>
        <div className="h-[320px] bg-nav-hover rounded-lg" />
      </div>
    );
  }

  const chartData = (data || []).slice(0, 15).map((d) => ({
    name: d.department_name?.length > 12
      ? d.department_name.slice(0, 12) + "…"
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
    <div className="card-container p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
        <DateRangePicker value={dateRange} onChange={onDateChange} />
      </div>

      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 0, right: 20, top: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 11, fill: "#94A3B8" }} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} width={100} />
          <Tooltip
            contentStyle={{ borderRadius: 8, border: "1px solid #EAECF0", boxShadow: "0px 4px 12px rgba(0,0,0,0.06)" }}
            formatter={(value: number, name: string) => [`${value}%`, name]}
            labelFormatter={(label, payload) => payload?.[0]?.payload?.fullName || label}
          />
          <Legend
            onClick={handleLegendClick}
            wrapperStyle={{ cursor: "pointer" }}
            formatter={(value: string) => {
              const segKey = SEGMENTS.find(s => s.label === value)?.key || value;
              return (
                <span style={{ color: isHidden(segKey) ? "#CBD5E1" : "#64748B", fontSize: 12 }}>
                  {value}
                </span>
              );
            }}
          />
          {SEGMENTS.map((seg) => (
            <Bar key={seg.key} dataKey={seg.key} name={seg.label} stackId="a" barSize={16} hide={isHidden(seg.key)} radius={seg.key === "training_pct" ? [0, 4, 4, 0] : 0}>
              {chartData.map((_, i) => (
                <Cell key={i} fill={seg.color} />
              ))}
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
