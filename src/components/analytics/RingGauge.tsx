import { useId } from "react";

interface RingGaugeProps {
  /** 0..100 */
  value: number;
  size?: number;
  thickness?: number;
  color?: string;
  trackColor?: string;
  /** Center content (e.g. the big number) */
  children?: React.ReactNode;
}

/** Circular progress gauge for rate KPIs — SVG, CSS-animated sweep. */
export default function RingGauge({
  value,
  size = 64,
  thickness = 7,
  color = "#1677FF",
  trackColor = "#F1F5F9",
  children,
}: RingGaugeProps) {
  const clamped = Math.max(0, Math.min(100, value));
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - clamped / 100);
  const gid = useId();

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.75} />
            <stop offset="100%" stopColor={color} />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} stroke={trackColor} strokeWidth={thickness} fill="none" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke={`url(#${gid})`}
          strokeWidth={thickness}
          strokeLinecap="round"
          fill="none"
          strokeDasharray={c}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.9s cubic-bezier(0.22, 1, 0.36, 1)" }}
        />
      </svg>
      {children != null && (
        <div className="absolute inset-0 flex items-center justify-center">{children}</div>
      )}
    </div>
  );
}
