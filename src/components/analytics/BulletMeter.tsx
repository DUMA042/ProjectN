import { ACCENT, MUTED } from "@/lib/analyticsColors";
import { fmtNum } from "@/lib/format";

interface BulletMeterProps {
  label: string;
  value: number;
  max: number;
  /** Reference marker (e.g. previous-period value). */
  previous?: number | null;
  unit?: string;
  color?: string;
  /** When set, the fill turns danger-colored below this threshold. */
  dangerBelow?: number;
}

/** Bullet chart — value bar + previous-period marker on a track. */
export default function BulletMeter({
  label, value, max, previous, unit = "", color = ACCENT, dangerBelow,
}: BulletMeterProps) {
  const safeMax = max > 0 ? max : 1;
  const pct = Math.max(0, Math.min(100, (value / safeMax) * 100));
  const prevPct = previous != null ? Math.max(0, Math.min(100, (previous / safeMax) * 100)) : null;
  const fill = dangerBelow != null && value < dangerBelow ? "#FF4D4F" : color;

  return (
    <div>
      <div className="flex items-baseline justify-between mb-1">
        <span className="text-[11px] uppercase tracking-wide text-text-muted">{label}</span>
        <span className="text-xs font-semibold text-text-primary tabular-nums">
          {fmtNum(value, Number.isInteger(value) ? 0 : 1)}{unit}
          {previous != null && <span className="text-text-muted font-normal"> / {fmtNum(previous, 0)}{unit}</span>}
        </span>
      </div>
      <div className="relative h-2 rounded-full bg-nav-hover overflow-visible">
        <div
          className="absolute inset-y-0 left-0 rounded-full"
          style={{ width: `${pct}%`, backgroundColor: fill, transition: "width 0.7s cubic-bezier(0.22, 1, 0.36, 1)" }}
        />
        {prevPct != null && (
          <div
            className="absolute -inset-y-[2px] w-[2px] rounded"
            style={{ left: `${prevPct}%`, backgroundColor: MUTED }}
            title={`Previous: ${previous}`}
          />
        )}
      </div>
    </div>
  );
}
