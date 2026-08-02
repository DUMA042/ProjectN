import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

interface BarChartCardProps {
  title: string;
  data: { label: string; value: number }[];
  loading?: boolean;
  height?: number;
}

export default function BarChartCard({
  title,
  data,
  loading,
  height = 280,
}: BarChartCardProps) {
  if (loading) {
    return (
      <div className="card-container p-5 animate-pulse">
        <div className="h-5 w-48 bg-nav-hover rounded mb-4" />
        <div className="h-[280px] bg-nav-hover rounded-lg" />
      </div>
    );
  }

  const chartData = data.map((d, i) => ({
    name: d.label.length > 15 ? d.label.slice(0, 15) + "…" : d.label,
    value: d.value,
    fullName: d.label,
    isMax: d.value === Math.max(...data.map((x) => x.value)),
  }));

  return (
    <div className="card-container p-5">
      <h3 className="text-sm font-semibold text-text-primary mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 0, right: 20, top: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 11, fill: "#94A3B8" }} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} width={120} />
          <Tooltip
            contentStyle={{ borderRadius: 8, border: "1px solid #EAECF0", boxShadow: "0px 4px 12px rgba(0,0,0,0.06)" }}
            formatter={(value: number) => [value.toLocaleString(), null]}
            labelFormatter={(label, payload) => payload?.[0]?.payload?.fullName || label}
          />
          <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={16}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={entry.isMax ? "#0F172A" : "#E2E8F0"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
