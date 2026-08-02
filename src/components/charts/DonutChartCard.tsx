import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";

interface DonutSegment {
  name: string;
  value: number;
  color: string;
}

interface DonutChartCardProps {
  title: string;
  data: DonutSegment[];
  centerLabel?: string;
  loading?: boolean;
  height?: number;
}

export default function DonutChartCard({
  title,
  data,
  centerLabel,
  loading,
  height = 300,
}: DonutChartCardProps) {
  if (loading) {
    return (
      <div className="card-container p-5 animate-pulse">
        <div className="h-5 w-48 bg-nav-hover rounded mb-4" />
        <div className="h-[300px] bg-nav-hover rounded-lg" />
      </div>
    );
  }

  const total = data.reduce((sum, d) => sum + d.value, 0);

  return (
    <div className="card-container p-5">
      <h3 className="text-sm font-semibold text-text-primary mb-4">{title}</h3>

      <div className="relative">
        <ResponsiveContainer width="100%" height={height}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={70}
              outerRadius={110}
              paddingAngle={2}
              dataKey="value"
              strokeWidth={0}
              isAnimationActive
            >
              {data.map((segment, i) => (
                <Cell key={i} fill={segment.color} />
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
              <div className="text-2xl font-bold text-text-primary">
                {centerLabel}
              </div>
              <div className="text-xs text-text-secondary">Total</div>
            </div>
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-4 justify-center mt-2">
        {data.map((segment) => (
          <div key={segment.name} className="flex items-center gap-2">
            <span
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: segment.color }}
            />
            <span className="text-xs text-text-secondary">
              {segment.name}{" "}
              <span className="font-medium text-text-primary">
                {((segment.value / total) * 100).toFixed(0)}%
              </span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
