import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";

export interface CompositionDatum {
  name: string;
  value: number;
  color?: string;
}

const PALETTE = ["#1677FF", "#52C41A", "#FAAD14", "#722ED1", "#FF4D4F", "#13C2C2", "#EB2F96", "#8C8C8C"];

interface CompositionChartProps {
  title: string;
  data: CompositionDatum[];
  type?: "bar" | "donut";
  color?: string;
  onSelect?: (name: string) => void;
  loading?: boolean;
}

export default function CompositionChart({
  title,
  data,
  type = "bar",
  color = "#1677FF",
  onSelect,
  loading,
}: CompositionChartProps) {
  return (
    <div className="card-container p-4">
      <h4 className="text-xs font-semibold text-text-primary mb-3">{title}</h4>
      {loading ? (
        <div className="h-[220px] bg-nav-hover rounded animate-pulse" />
      ) : data.length === 0 ? (
        <p className="text-xs text-text-muted text-center py-16">No data</p>
      ) : type === "donut" ? (
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius={48}
              outerRadius={78}
              paddingAngle={2}
              strokeWidth={0}
              onClick={(d: any) => onSelect?.(d?.name)}
              cursor={onSelect ? "pointer" : "default"}
            >
              {data.map((d, i) => (
                <Cell key={i} fill={d.color || PALETTE[i % PALETTE.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ borderRadius: 8, border: "1px solid #EAECF0", fontSize: 12 }}
              formatter={(v: number, n: string) => [v.toLocaleString(), n]}
            />
            <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
          </PieChart>
        </ResponsiveContainer>
      ) : (
        <ResponsiveContainer width="100%" height={Math.max(160, data.length * 24)}>
          <BarChart data={data} layout="vertical" margin={{ left: 4, right: 20, top: 4, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 10, fill: "#94A3B8" }} axisLine={false} tickLine={false} />
            <YAxis
              type="category"
              dataKey="name"
              width={120}
              tick={{ fontSize: 10, fill: "#64748B" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{ borderRadius: 8, border: "1px solid #EAECF0", fontSize: 12 }}
              formatter={(v: number, n: string) => [v.toLocaleString(), n]}
              cursor={{ fill: "#F5F5F5" }}
            />
            <Bar
              dataKey="value"
              fill={color}
              radius={[0, 3, 3, 0]}
              onClick={(d: any) => onSelect?.(d?.name)}
              cursor={onSelect ? "pointer" : "default"}
            />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
