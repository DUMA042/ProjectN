import { CATEGORICAL } from "@/lib/analyticsColors";

export interface WafflePart {
  name: string;
  value: number;
  color?: string;
}

interface WaffleChartProps {
  parts: WafflePart[];
  /** Denominator; defaults to the sum of parts. Remainder renders as "Other". */
  total?: number;
  dotSize?: number;
  onPartClick?: (name: string) => void;
}

function allocDots(parts: WafflePart[], total?: number): { part: WafflePart; dots: number }[] {
  const sum = parts.reduce((s, p) => s + p.value, 0);
  const denom = total ?? sum;
  const raw = parts.map((p) => (denom > 0 ? (p.value / denom) * 100 : 0));
  const dots: number[] = raw.map((r) => Math.floor(r));
  let left = 100 - dots.reduce((s, d) => s + d, 0);
  // distribute remainder by largest fractional part
  const order = raw.map((r, i) => ({ i, frac: r - Math.floor(r) })).sort((a, b) => b.frac - a.frac);
  for (const { i } of order) {
    if (left <= 0) break;
    dots[i] = (dots[i] ?? 0) + 1;
    left -= 1;
  }
  return parts.map((p, i) => ({ part: p, dots: dots[i] }));
}

/** 10×10 dot-grid composition infographic — "23% on leave" at a glance. */
export default function WaffleChart({ parts, total, dotSize = 9, onPartClick }: WaffleChartProps) {
  const alloc = allocDots(parts, total);
  const seq: (WafflePart | null)[] = [];
  alloc.forEach(({ part, dots }) => {
    for (let i = 0; i < dots; i++) seq.push(part);
  });
  while (seq.length < 100) seq.push(null);
  const sum = parts.reduce((s, p) => s + p.value, 0);
  const denom = total ?? sum;
  const other = Math.max(0, denom - sum);

  return (
    <div className="flex items-start gap-4">
      <div
        className="grid grid-rows-10 gap-[2px] flex-shrink-0"
        style={{ gridTemplateColumns: `repeat(10, ${dotSize}px)`, gridAutoRows: `${dotSize}px` }}
      >
        {seq.slice(0, 100).map((p, i) => (
          <span
            key={i}
            title={p ? `${p.name}: ${p.value}` : "Other"}
            className="rounded-[2px]"
            style={{ width: dotSize, height: dotSize, backgroundColor: p ? p.color || CATEGORICAL[0] : "#E2E8F0" }}
          />
        ))}
      </div>
      <div className="flex-1 min-w-0 space-y-1.5">
        {alloc.map(({ part, dots }, i) => (
          <button
            key={part.name}
            onClick={() => onPartClick?.(part.name)}
            className={`w-full flex items-center gap-2 text-left ${onPartClick ? "hover:opacity-80 cursor-pointer" : "cursor-default"}`}
          >
            <span
              className="w-2.5 h-2.5 rounded-[3px] flex-shrink-0"
              style={{ backgroundColor: part.color || CATEGORICAL[i % CATEGORICAL.length] }}
            />
            <span className="text-xs text-text-secondary truncate flex-1">{part.name}</span>
            <span className="text-xs font-semibold text-text-primary tabular-nums">
              {part.value}
              <span className="text-text-muted font-normal"> · {dots}%</span>
            </span>
          </button>
        ))}
        {other > 0 && (
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-[3px] bg-[#E2E8F0]" />
            <span className="text-xs text-text-muted flex-1">Other</span>
            <span className="text-xs text-text-muted tabular-nums">{other}</span>
          </div>
        )}
      </div>
    </div>
  );
}
