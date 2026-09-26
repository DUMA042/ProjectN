import { useEffect, useRef, useState } from "react";
import { ArrowUp, ArrowDown, Minus } from "lucide-react";
import RingGauge from "./RingGauge";

export interface Kpi {
  label: string;
  value: string | number;
  sub?: string;
  /** Absolute change vs previous period (pp for rates, count otherwise). */
  delta?: number | null;
  /** Direction semantics: up_good (default) colors rising deltas green. */
  polarity?: "up_good" | "up_bad" | null;
  /** 0..100 — renders a ring gauge around the value instead of a plain number. */
  ring?: number | null;
  /** Ring stroke color (e.g. semantic blue↔red); defaults to accent. */
  color?: string;
  /** Recent values for the inline sparkline. */
  sparkline?: number[];
}

function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

function useCountUp(target: number | null, duration = 700): number | null {
  const [display, setDisplay] = useState(target);
  const fromRef = useRef(target);
  useEffect(() => {
    if (target == null) return;
    if (prefersReducedMotion()) {
      fromRef.current = target;
      setDisplay(target);
      return;
    }
    const from = fromRef.current ?? 0;
    if (from === target) return;
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplay(Math.round(from + (target - from) * eased));
      if (t < 1) raf = requestAnimationFrame(tick);
      else fromRef.current = target;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);
  return display;
}

function Sparkline({ values, color = "#1677FF" }: { values: number[]; color?: string }) {
  if (values.length < 2) return null;
  const w = 56;
  const h = 18;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const pts = values
    .map((v, i) => `${(i / (values.length - 1)) * w},${h - 2 - ((v - min) / span) * (h - 4)}`)
    .join(" ");
  return (
    <svg width={w} height={h} className="flex-shrink-0">
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" strokeLinecap="round" opacity={0.55} />
    </svg>
  );
}

function DeltaChip({ delta, polarity }: { delta: number; polarity?: "up_good" | "up_bad" | null }) {
  if (!Number.isFinite(delta)) return null;
  const rising = delta > 0;
  const falling = delta < 0;
  const good = polarity === "up_bad" ? falling : rising;
  const neutral = delta === 0;
  const cls = neutral
    ? "bg-nav-hover text-text-muted"
    : good
      ? "bg-badge-green-bg text-badge-green-text"
      : "bg-badge-red-bg text-badge-red-text";
  return (
    <span className={`inline-flex items-center gap-0.5 text-[10px] font-medium px-1.5 py-0.5 rounded-full ${cls}`}>
      {neutral ? <Minus size={10} /> : rising ? <ArrowUp size={10} /> : <ArrowDown size={10} />}
      {Math.abs(Math.round(delta * 10) / 10)}
    </span>
  );
}

export default function KpiStrip({ items, loading }: { items: Kpi[]; loading?: boolean }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-8 gap-3">
      {items.map((k) => (
        <KpiTile key={k.label} kpi={k} loading={loading} />
      ))}
    </div>
  );
}

function KpiTile({ kpi, loading }: { kpi: Kpi; loading?: boolean }) {
  const numeric = typeof kpi.value === "number" ? kpi.value : null;
  const display = useCountUp(numeric);
  const shown = numeric != null ? display : kpi.value;

  return (
    <div className="card-container p-4 flex items-start justify-between gap-2">
      {loading ? (
        <>
          <div className="flex-1">
            <div className="h-3 w-20 bg-nav-hover rounded mb-2" />
            <div className="h-6 w-16 bg-nav-hover rounded" />
          </div>
        </>
      ) : (
        <>
          <div className="min-w-0">
            <p className="text-xs text-text-secondary truncate">{kpi.label}</p>
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              {kpi.ring != null ? (
                <RingGauge value={kpi.ring} size={46} thickness={5} color={kpi.color}>
                  <span className="text-[11px] font-bold text-text-primary tabular-nums">{shown}</span>
                </RingGauge>
              ) : (
                <p className="text-xl font-bold text-text-primary tabular-nums">{shown}</p>
              )}
              {kpi.delta != null && <DeltaChip delta={kpi.delta} polarity={kpi.polarity} />}
            </div>
            {kpi.sub && <p className="text-[11px] text-text-muted mt-0.5 truncate">{kpi.sub}</p>}
          </div>
          {kpi.sparkline && kpi.sparkline.length >= 2 && (
            <div className="mt-4">
              <Sparkline values={kpi.sparkline} />
            </div>
          )}
        </>
      )}
    </div>
  );
}
