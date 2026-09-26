import { useId } from "react";
import {
  AreaChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { fmtDateShort } from "@/lib/format";

export interface TrendPoint {
  label: string;
  value: number;
}

export interface BandPoint {
  label: string;
  low: number;
  high: number;
}

interface TrendChartProps {
  title?: string;
  data: TrendPoint[];
  compareData?: TrendPoint[];
  /** Continuation series rendered dashed with a ±band (forecast). */
  projectionData?: TrendPoint[];
  bandData?: BandPoint[];
  suffix?: string;
  loading?: boolean;
  height?: number;
  compact?: boolean;
  /** Fires with the x-axis label of the clicked point (investigation hook). */
  onPointClick?: (label: string) => void;
  /** Subtitle line under the title. */
  subtitle?: string;
}

/** Gradient-area trend line with optional previous-period overlay and
 * dashed projection + ±band. The workhorse chart of the workspace. */
export default function TrendChart({
  title, data, compareData, projectionData, bandData, suffix = "", loading, height = 220, compact, onPointClick, subtitle,
}: TrendChartProps) {
  const gid = useId();
  const label = (v: string) => (suffix === "%" ? `${v}` : fmtDateShort(v));

  const merged: Record<string, number | string | null>[] = data.map((d) => ({
    label: d.label,
    Current: d.value,
    ...(compareData ? { Previous: compareData.find((c) => c.label === d.label)?.value ?? null } : {}),
  }));

  if (projectionData && projectionData.length > 0) {
    // connect the projection to the last actual point
    const last = data[data.length - 1];
    const bridge = last ? [{ label: last.label, value: last.value }] : [];
    const projLabels = new Set<string>();
    [...bridge, ...projectionData].forEach((p) => projLabels.add(p.label));
    projLabels.forEach((lbl) => {
      const row: Record<string, number | string | null> = merged.find((r) => r.label === lbl) || { label: lbl, Current: null };
      const fromActual = lbl === last?.label;
      row.Projected = fromActual ? (last?.value ?? null) : (projectionData.find((p) => p.label === lbl)?.value ?? null);
      const band = bandData?.find((b) => b.label === lbl);
      if (band) {
        row.BandLow = band.low;
        row.BandHigh = band.high;
      }
      if (!merged.find((r) => r.label === lbl)) merged.push(row);
    });
  }

  const body = loading ? (
    <div style={{ height }} className="bg-nav-hover rounded animate-pulse" />
  ) : merged.length === 0 ? (
    <p className="text-xs text-text-muted text-center" style={{ lineHeight: `${height}px` }}>No data</p>
  ) : (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart
        data={merged}
        margin={{ left: -10, right: 10, top: 6, bottom: 0 }}
        onClick={(state: { activeLabel?: string | number }) => {
          if (onPointClick && state?.activeLabel != null) onPointClick(String(state.activeLabel));
        }}
        style={onPointClick ? { cursor: "pointer" } : undefined}
      >
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#1677FF" stopOpacity={0.22} />
            <stop offset="100%" stopColor="#1677FF" stopOpacity={0.01} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
        <XAxis dataKey="label" tickFormatter={label} tick={{ fontSize: 10, fill: "#94A3B8" }} interval="preserveStartEnd" />
        <YAxis tick={{ fontSize: 10, fill: "#94A3B8" }} tickFormatter={(v) => `${v}${suffix}`} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={{ borderRadius: 8, border: "1px solid #EAECF0", fontSize: 12 }}
          formatter={(v: number, n: string) => [v != null ? `${v}${suffix}` : "—", n]}
          cursor={onPointClick ? { stroke: "#CBD5E1", strokeWidth: 1 } : undefined}
        />
        {!compact && <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />}
        {bandData && bandData.length > 0 && (
          <Area type="monotone" dataKey="BandHigh" stroke="none" fill="#1677FF" fillOpacity={0.08} legendType="none" connectNulls />
        )}
        {bandData && bandData.length > 0 && (
          <Area type="monotone" dataKey="BandLow" stroke="none" fill="#FFFFFF" fillOpacity={0.9} legendType="none" connectNulls />
        )}
        <Area
          type="monotone" dataKey="Current" stroke="#1677FF" strokeWidth={2}
          fill={`url(#${gid})`} dot={{ r: 2 }} activeDot={{ r: 4, cursor: onPointClick ? "pointer" : "default" }} connectNulls
          animationDuration={600}
        />
        {compareData && (
          <Line type="monotone" dataKey="Previous" stroke="#94A3B8" strokeWidth={1.5} strokeDasharray="4 3" dot={false} connectNulls />
        )}
        {projectionData && projectionData.length > 0 && (
          <Line type="monotone" dataKey="Projected" stroke="#1677FF" strokeWidth={2} strokeDasharray="5 4" dot={false} connectNulls />
        )}
      </AreaChart>
    </ResponsiveContainer>
  );

  if (compact) return body;
  return (
    <div className="card-container p-4">
      {title && <h4 className="text-xs font-semibold text-text-primary">{title}</h4>}
      {subtitle && <p className="text-[11px] text-text-muted mt-0.5 mb-3">{subtitle}</p>}
      {!subtitle && <div className="mb-3" />}
      {body}
    </div>
  );
}
