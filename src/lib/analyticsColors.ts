/** Shared analytics color language — status palette, ramps, categorical set. */

export const ACCENT = "#1677FF";
export const ACCENT_DEEP = "#0958D9";
export const ACCENT_SOFT = "#E6F4FF";
export const SUCCESS = "#52C41A";
export const DANGER = "#FF4D4F";
export const WARNING = "#FAAD14";
export const INFO = "#1677FF";
export const MUTED = "#94A3B8";

/** One status palette used everywhere: calendar, stacked bars, legends. */
export const STATUS_COLORS: Record<string, string> = {
  present: SUCCESS,
  late: WARNING,
  absent: DANGER,
  leave: "#722ED1",
  training: "#13C2C2",
  weekend: "#CBD5E1",
  holiday: "#94A3B8",
  inactive: "#E2E8F0",
  upcoming: "#F1F5F9",
};

export const STATUS_LABELS: Record<string, string> = {
  present: "Present",
  late: "Late",
  absent: "Absent",
  leave: "Leave",
  training: "Training",
  weekend: "Weekend",
  holiday: "Holiday",
  inactive: "Inactive",
  upcoming: "Upcoming",
};

/** Categorical palette for composition charts (dimension series). */
export const CATEGORICAL = [
  "#1677FF", "#52C41A", "#FAAD14", "#FF4D4F", "#722ED1", "#13C2C2", "#EB2F96", "#FA8C16",
];

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

function rgbToHex(r: number, g: number, b: number): string {
  const c = (v: number) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0");
  return `#${c(r)}${c(g)}${c(b)}`;
}

/** Sequential single-hue ramp (0..1): accent soft → accent deep. */
export function seqColor(t: number): string {
  const clamped = Math.max(0, Math.min(1, t));
  const a = hexToRgb(ACCENT_SOFT);
  const b = hexToRgb(ACCENT_DEEP);
  return rgbToHex(a[0] + (b[0] - a[0]) * clamped, a[1] + (b[1] - a[1]) * clamped, a[2] + (b[2] - a[2]) * clamped);
}

/** Diverging ramp for deltas: −1 → red, 0 → neutral, +1 → green. */
export function divColor(v: number): string {
  const clamped = Math.max(-1, Math.min(1, v));
  if (clamped >= 0) {
    const a = hexToRgb("#F1F5F9");
    const b = hexToRgb(SUCCESS);
    const t = clamped;
    return rgbToHex(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t);
  }
  const a = hexToRgb("#F1F5F9");
  const b = hexToRgb(DANGER);
  const t = -clamped;
  return rgbToHex(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t);
}

// ── Semantic blue↔red metric scale ──────────────────────────────────────────
// Metric VALUES read as good (blue) ↔ bad (red) without looking at numbers.
// Direction comes from the metric's polarity; the pivot (the neutral line) is
// either fixed in the metric catalog (percentage metrics) or the median of the
// data in view (counts, which have no absolute good/bad line).

export interface SemanticMeta {
  polarity?: "up_good" | "up_bad" | null;
  /** Fixed good/bad line for the metric (e.g. attendance_rate → 60). */
  pivot?: number | null;
}

const GOOD_LIGHT = "#E6F4FF";
const GOOD_DEEP = "#0958D9";
const BAD_LIGHT = "#FFF1F0";
const BAD_DEEP = "#D4380D";

function mix(a: string, b: string, t: number): string {
  const ca = hexToRgb(a);
  const cb = hexToRgb(b);
  return rgbToHex(ca[0] + (cb[0] - ca[0]) * t, ca[1] + (cb[1] - ca[1]) * t, ca[2] + (cb[2] - ca[2]) * t);
}

export function median(values: number[]): number {
  if (values.length === 0) return 0;
  const s = [...values].filter((v) => Number.isFinite(v)).sort((a, b) => a - b);
  if (s.length === 0) return 0;
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

/**
 * Build a value→color scale for one metric across the data currently in view.
 * Fixed-pivot metrics keep their catalog pivot with a ±40-unit spread;
 * relative metrics pivot on the median with a spread that reaches full
 * intensity at the data extremes.
 */
export function makeSemanticScale(meta: SemanticMeta, values: number[]): (v: number) => string {
  const pivot = meta.pivot != null ? meta.pivot : median(values);
  const spread =
    meta.pivot != null
      ? 40
      : Math.max(...values.map((v) => Math.abs(v - pivot)), 1);
  return (v: number) => semanticColor(v, meta, pivot, spread);
}

/** Color one value on the blue(good)↔red(bad) scale. */
export function semanticColor(
  value: number,
  meta: SemanticMeta,
  pivot: number,
  spread: number
): string {
  if (!Number.isFinite(value)) return "#E2E8F0";
  const d = meta.polarity === "up_bad" ? pivot - value : value - pivot;
  const t = Math.max(-1, Math.min(1, d / (spread || 1)));
  return t >= 0 ? mix(GOOD_LIGHT, GOOD_DEEP, t) : mix(BAD_LIGHT, BAD_DEEP, -t);
}

/** Readable text color on top of a background hex (white on dark fills). */
export function readableFg(bg: string): string {
  const [r, g, b] = hexToRgb(bg);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance < 0.62 ? "#FFFFFF" : "#0F172A";
}
