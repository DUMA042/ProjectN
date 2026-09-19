import { useState } from "react";
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
import { Download } from "lucide-react";
import DateRangePicker from "@/components/ui/DateRangePicker";
import PercentCountToggle from "@/components/ui/PercentCountToggle";
import { useClickableLegend } from "@/lib/chartUtils";
import { exportToCSV } from "@/lib/csvExport";
import type { DateRange } from "@/components/ui/DateRangePicker";

const SEGMENTS = [
  { id: "attendance", label: "Attendance", color: "#52C41A", pctKey: "attendance_pct", countKey: "attendance_count" },
  { id: "absent", label: "Absent", color: "#FF4D4F", pctKey: "absent_pct", countKey: "absent_count" },
  { id: "leave", label: "Leave", color: "#FAAD14", pctKey: "leave_pct", countKey: "leave_count" },
  { id: "training", label: "Training", color: "#1677FF", pctKey: "training_pct", countKey: "training_count" },
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
  const [mode, setMode] = useState<"pct" | "count">("pct");

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

  const chartData = (data || []).map((d) => {
    const row: Record<string, any> = {
      name: d.department_name?.length > 14
        ? d.department_name.slice(0, 14) + "…"
        : d.department_name,
      fullName: d.department_name,
      total: d.total_staff,
    };
    for (const seg of SEGMENTS) {
      row[seg.pctKey] = d[seg.pctKey] ?? 0;
      row[seg.countKey] = d[seg.countKey] ?? 0;
    }
    return row;
  });

  const handleLegendClick = (entry: any) => {
    const seg = SEGMENTS.find((s) => s.label === entry.value);
    if (seg) toggle(seg.id);
  };

  if (!data || data.length === 0) {
    return (
      <div className="card-container p-5 h-[440px] flex flex-col">
        <div className="flex items-center justify-between mb-2 flex-wrap gap-2 flex-shrink-0">
          <div>
            <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
            <p className="text-xs text-text-secondary mt-0.5">Clustered breakdown for all {location} departments</p>
          </div>
          <div className="flex items-center gap-2">
            <PercentCountToggle value={mode} onChange={setMode} />
            <button
              onClick={() => exportToCSV(data || [], "department_attendance_perf", dateRange)}
              title="Export CSV"
              aria-label="Export CSV"
              className="p-2 rounded-btn text-text-muted hover:text-accent hover:bg-nav-hover transition-colors"
            >
              <Download size={14} />
            </button>
            <DateRangePicker value={dateRange} onChange={onDateChange} />
          </div>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center text-text-muted gap-2">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" opacity={0.4}>
            <rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h18M9 21V9" />
          </svg>
          <p className="text-sm font-medium">No attendance data</p>
          <p className="text-xs">Try selecting a different date range or location</p>
        </div>
      </div>
    );
  }

  const isPct = mode === "pct";

  return (
    <div className="card-container p-5 h-[440px] flex flex-col justify-between">
      <div className="flex items-center justify-between mb-2 flex-wrap gap-2 flex-shrink-0">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
          <p className="text-xs text-text-secondary mt-0.5">Clustered breakdown for all {location} departments</p>
        </div>
        <div className="flex items-center gap-2">
          <PercentCountToggle value={mode} onChange={setMode} />
          <button
            onClick={() => exportToCSV(data, "department_attendance_perf", dateRange)}
            title="Export CSV"
            aria-label="Export CSV"
            className="p-2 rounded-btn text-text-muted hover:text-accent hover:bg-nav-hover transition-colors"
          >
            <Download size={14} />
          </button>
          <DateRangePicker value={dateRange} onChange={onDateChange} />
        </div>
      </div>

      <div className="flex-1 min-h-0 pt-2">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ left: -15, right: 10, top: 10, bottom: 55 }}>
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
              unit={isPct ? "%" : undefined}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{ borderRadius: 8, border: "1px solid #EAECF0", boxShadow: "0px 4px 12px rgba(0,0,0,0.06)" }}
              formatter={(value: number, name: string) => [isPct ? `${value}%` : value.toLocaleString(), name]} 
              labelFormatter={(label, payload) => payload?.[0]?.payload?.fullName || label}
            />
            <Legend
              onClick={handleLegendClick}
              iconType="square"
              iconSize={10}
              payload={SEGMENTS.map((s) => ({ value: s.label, color: isHidden(s.id) ? "#CBD5E1" : s.color, type: "square" as const }))}
              wrapperStyle={{ cursor: "pointer", paddingTop: 28 }}
            formatter={(value: string) => {
              const seg = SEGMENTS.find((s) => s.label === value);
              const key = seg ? seg.id : value;
              return (
                <span className={isHidden(key) ? "opacity-40" : ""} style={{ color: "#64748B", fontSize: 12 }}>
                  {value}
                </span>
              );
            }}
            />
            {SEGMENTS.map((seg) => (
              <Bar
                key={seg.id}
                dataKey={isPct ? seg.pctKey : seg.countKey}
                name={seg.label}
                fill={isHidden(seg.id) ? "transparent" : seg.color}
                radius={[3, 3, 0, 0]}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
