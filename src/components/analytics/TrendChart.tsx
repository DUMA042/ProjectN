import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";

export interface TrendPoint {
  label: string;
  value: number;
}

interface TrendChartProps {
  title: string;
  data: TrendPoint[];
  compareData?: TrendPoint[];
  suffix?: string;
  loading?: boolean;
}

export default function TrendChart({ title, data, compareData, suffix = "", loading }: TrendChartProps) {
  const merged = data.map((d, i) => ({
    label: d.label,
    Current: d.value,
    ...(compareData ? { Previous: compareData[i]?.value ?? null } : {}),
  }));

  return (
    <div className="card-container p-4">
      <h4 className="text-xs font-semibold text-text-primary mb-3">{title}</h4>
      {loading ? (
        <div className="h-[220px] bg-nav-hover rounded animate-pulse" />
      ) : merged.length === 0 ? (
        <p className="text-xs text-text-muted text-center py-16">No data</p>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={merged} margin={{ left: -10, right: 10, top: 6, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
            <XAxis dataKey="label" tick={{ fontSize: 10, fill: "#94A3B8" }} interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: 10, fill: "#94A3B8" }} tickFormatter={(v) => `${v}${suffix}`} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{ borderRadius: 8, border: "1px solid #EAECF0", fontSize: 12 }}
              formatter={(v: number, n: string) => [`${v}${suffix}`, n]}
            />
            <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
            <Line type="monotone" dataKey="Current" stroke="#1677FF" strokeWidth={2} dot={{ r: 3 }} connectNulls />
            {compareData && (
              <Line type="monotone" dataKey="Previous" stroke="#94A3B8" strokeWidth={1.5} strokeDasharray="4 3" dot={false} connectNulls />
            )}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
