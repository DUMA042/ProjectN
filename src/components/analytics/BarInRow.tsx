import { ACCENT } from "@/lib/analyticsColors";

interface BarInRowProps {
  value: number;
  max: number;
  color?: string;
  format?: (n: number) => string;
  className?: string;
  /** Bar fill strength (0..1) — stronger for semantic-colored bars. */
  barOpacity?: number;
}

/** Table-cell value with a proportional bar behind it — every ranking row
 * becomes a mini infographic. */
export default function BarInRow({ value, max, color = ACCENT, format, className = "", barOpacity = 0.18 }: BarInRowProps) {
  const safeMax = max > 0 ? max : 1;
  const pct = Math.max(0, Math.min(100, (Math.abs(value) / safeMax) * 100));
  const text = format ? format(value) : String(value);
  return (
    <div className={`relative min-w-[90px] py-0.5 ${className}`}>
      <span
        className="absolute inset-y-[2px] left-0 rounded-r-[3px]"
        style={{ width: `${pct}%`, backgroundColor: color, opacity: barOpacity, transition: "width 0.5s ease" }}
      />
      <span className="relative text-xs font-medium text-text-primary tabular-nums">{text}</span>
    </div>
  );
}
