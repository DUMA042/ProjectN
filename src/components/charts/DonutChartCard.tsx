import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import DateRangePicker from "@/components/ui/DateRangePicker";
import { useClickableLegend } from "@/lib/chartUtils";
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
  loading?: boolean;
  height?: number;
}

export default function DonutChartCard({
  title,
  data,
  centerLabel,
  dateRange,
  onDateChange,
  loading,
  height = 280,
}: DonutChartCardProps) {
  const { isHidden, toggle } = useClickableLegend();

  if (loading) {
    return (
      <div className="card-container p-5 animate-pulse">
        <div className="flex justify-between mb-4">
          <div className="h-5 w-48 bg-nav-hover rounded" />
          <div className="h-8 w-28 bg-nav-hover rounded-btn" />
        </div>
        <div className="h-[280px] bg-nav-hover rounded-lg" />
      </div>
    );
  }

  const visibleData = data.filter((d) => !isHidden(d.name));
  const total = visibleData.reduce((sum, d) => sum + d.value, 0);

  const handleLegendClick = (entry: any) => {
    toggle(entry.value);
  };

  return (
    <div className="card-container p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
        <DateRangePicker value={dateRange} onChange={onDateChange} />
      </div>

      <div className="relative">
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
              {visibleData.map((_, i) => (
                <Cell key={i} fill={data[i]?.color ?? "#CBD5E1"} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                borderRadius: 8,
                border: "1px solid #EAECF0",
                boxShadow: "0px 4px 12px rgba(0,0,0,0.06)",
              }}
              formatter={(value: number, name: string) => [
                `${value.toLocaleString()} (${((value / total) * 100).toFixed(1)}%)`,
                name,
              ]}
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

      <Legend
        onClick={handleLegendClick}
        wrapperStyle={{ cursor: "pointer", paddingTop: 8 }}
        formatter={(value: string) => (
          <span
            style={{
              color: isHidden(value) ? "#CBD5E1" : "#64748B",
              fontSize: 12,
            }}
          >
            {value}{" "}
            {!isHidden(value) && (
              <span style={{ fontWeight: 600, color: "#0F172A" }}>
                {data.find((d) => d.name === value)?.percentage ?? 0}%
              </span>
            )}
          </span>
        )}
      />
    </div>
  );
}
