import { useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { Download } from "lucide-react";
import DateRangePicker from "@/components/ui/DateRangePicker";
import PercentCountToggle from "@/components/ui/PercentCountToggle";
import { useClickableLegend } from "@/lib/chartUtils";
import { exportToCSV } from "@/lib/csvExport";
import type { DateRange } from "@/components/ui/DateRangePicker";

interface DonutSegment {
  name: string;
  value: number;
  color: string;
  percentage?: number;
}

interface DonutChartCardProps {
  title: string;
  data: DonutSegment[];
  centerLabel?: string;
  dateRange: DateRange;
  onDateChange: (range: DateRange) => void;
  selectedDepartment?: string;
  onDepartmentChange?: (dept: string) => void;
  departments?: string[];
  loading?: boolean;
  height?: number;
}

export default function DonutChartCard({
  title,
  data,
  centerLabel,
  dateRange,
  onDateChange,
  selectedDepartment = "",
  onDepartmentChange,
  departments = [],
  loading,
  height = 240,
}: DonutChartCardProps) {
  const { isHidden, toggle } = useClickableLegend();
  const [mode, setMode] = useState<"pct" | "count">("pct");

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

  const visibleData = data.filter((d) => !isHidden(d.name));
  const total = visibleData.reduce((sum, d) => sum + d.value, 0);

  const handleLegendClick = (entry: any) => {
    toggle(entry.value);
  };

  if (!data || data.length === 0) {
    return (
      <div className="card-container p-5 h-[440px] flex flex-col">
        <div className="flex items-center justify-between mb-2 flex-wrap gap-2 flex-shrink-0">
          <div>
            <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
            <p className="text-xs text-text-secondary mt-0.5">Filter by department & day/date range</p>
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
            <button
              onClick={() => exportToCSV([], "workforce_status_distribution", dateRange)}
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
            <circle cx="12" cy="12" r="10" /><path d="M12 8v4l3 3" />
          </svg>
          <p className="text-sm font-medium">No workforce data</p>
          <p className="text-xs">Try selecting a different date range or department</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card-container p-5 h-[440px] flex flex-col justify-between">
      <div className="flex items-center justify-between mb-2 flex-wrap gap-2 flex-shrink-0">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
          <p className="text-xs text-text-secondary mt-0.5">Filter by department & day/date range</p>
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
          <PercentCountToggle value={mode} onChange={setMode} />
          <button
            onClick={() => exportToCSV(data.map(d => ({ name: d.name, value: d.value, percentage: d.percentage ?? 0 })), "workforce_status_distribution", dateRange)}
            title="Export CSV"
            aria-label="Export CSV"
            className="p-2 rounded-btn text-text-muted hover:text-accent hover:bg-nav-hover transition-colors"
          >
            <Download size={14} />
          </button>
          <DateRangePicker value={dateRange} onChange={onDateChange} />
        </div>
      </div>

      <div className="relative flex-1 min-h-0 flex items-center justify-center">
        <ResponsiveContainer width="100%" height={height}>
          <PieChart>
            <Pie
              data={visibleData}
              cx="50%"
              cy="50%"
              innerRadius={65}
              outerRadius={100}
              paddingAngle={2}
              dataKey="value"
              strokeWidth={0}
              isAnimationActive
            >
              {visibleData.map((d, i) => (
                <Cell key={i} fill={d.color ?? "#CBD5E1"} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                borderRadius: 8,
                border: "1px solid #EAECF0",
                boxShadow: "0px 4px 12px rgba(0,0,0,0.06)",
              }}
              formatter={(value: number, name: string) =>
                mode === "pct"
                  ? [`${value.toLocaleString()} (${((value / total) * 100).toFixed(1)}%)`, name]
                  : [value.toLocaleString(), name]
              }
            />
            <Legend
              onClick={handleLegendClick}
              payload={data.map((d) => ({ value: d.name, color: isHidden(d.name) ? "#CBD5E1" : d.color, type: "square" as const }))}
              wrapperStyle={{ cursor: "pointer", paddingTop: 16 }}
              formatter={(value: string) => {
                const seg = data.find((d) => d.name === value);
                const label =
                  mode === "pct"
                    ? `${seg?.percentage ?? 0}%`
                    : (seg?.value ?? 0).toLocaleString();
                return (
                  <span className={isHidden(value) ? "opacity-40" : ""} style={{ color: "#64748B", fontSize: 12 }}>
                    {value}{" "}
                    {!isHidden(value) && (
                      <span style={{ fontWeight: 600, color: "#0F172A" }}>
                        {label}
                      </span>
                    )}
                  </span>
                );
              }}
            />
          </PieChart>
        </ResponsiveContainer>

        {centerLabel && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="text-center">
              <div className="text-2xl font-bold text-text-primary">{centerLabel}</div>
              <div className="text-xs text-text-secondary">Total</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
