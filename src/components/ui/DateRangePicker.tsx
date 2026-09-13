import { useState, useRef, useEffect, useCallback } from "react";
import { Calendar, X, ChevronLeft, ChevronRight } from "lucide-react";

export interface DateRange {
  startDate: string;
  endDate: string;
  label: string;
}

interface DateRangePickerProps {
  value: DateRange;
  onChange: (range: DateRange) => void;
}

export function getDefaultDateRange(): DateRange {
  const d = toISODate(new Date());
  return { startDate: d, endDate: d, label: "Today" };
}

function toISODate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function parseDate(s: string): Date {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

const PRESETS: { label: string; getRange: () => { start: string; end: string } }[] = [
  { label: "Today", getRange: () => { const d = toISODate(new Date()); return { start: d, end: d }; } },
  { label: "Yesterday", getRange: () => { const d = new Date(); d.setDate(d.getDate() - 1); const v = toISODate(d); return { start: v, end: v }; } },
  {
    label: "This Week",
    getRange: () => {
      const now = new Date();
      const monday = new Date(now);
      monday.setDate(now.getDate() - ((now.getDay() + 6) % 7));
      return { start: toISODate(monday), end: toISODate(now) };
    },
  },
  {
    label: "This Month",
    getRange: () => {
      const now = new Date();
      return { start: toISODate(new Date(now.getFullYear(), now.getMonth(), 1)), end: toISODate(now) };
    },
  },
  {
    label: "Last Month",
    getRange: () => {
      const now = new Date();
      return { start: toISODate(new Date(now.getFullYear(), now.getMonth() - 1, 1)), end: toISODate(new Date(now.getFullYear(), now.getMonth(), 0)) };
    },
  },
  {
    label: "Last 7 Days",
    getRange: () => {
      const now = new Date();
      const s = new Date(now); s.setDate(now.getDate() - 6);
      return { start: toISODate(s), end: toISODate(now) };
    },
  },
  {
    label: "Last 30 Days",
    getRange: () => {
      const now = new Date();
      const s = new Date(now); s.setDate(now.getDate() - 29);
      return { start: toISODate(s), end: toISODate(now) };
    },
  },
  {
    label: "Last 90 Days",
    getRange: () => {
      const now = new Date();
      const s = new Date(now); s.setDate(now.getDate() - 89);
      return { start: toISODate(s), end: toISODate(now) };
    },
  },
];

const WEEKDAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

function buildMonthGrid(year: number, month: number) {
  const firstDay = new Date(year, month, 1);
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const startCol = (firstDay.getDay() + 6) % 7;
  const weeks: (number | null)[][] = [];
  let cur: (number | null)[] = new Array(startCol).fill(null);
  for (let d = 1; d <= daysInMonth; d++) {
    cur.push(d);
    if (cur.length === 7) { weeks.push(cur); cur = []; }
  }
  if (cur.length) { while (cur.length < 7) cur.push(null); weeks.push(cur); }
  return weeks;
}

function formatDisplay(d: string) {
  if (!d) return "";
  return parseDate(d).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

// ── Single-month calendar sub-component ─────────────────────────────────────
function MonthCalendar({
  year, month,
  customStart, customEnd,
  onPrev, onNext, onDayClick,
}: {
  year: number; month: number;
  customStart: string; customEnd: string;
  onPrev: () => void; onNext: () => void;
  onDayClick: (y: number, m: number, d: number) => void;
}) {
  const weeks = buildMonthGrid(year, month);
  const monthName = new Date(year, month).toLocaleDateString("en-GB", { month: "long", year: "numeric" });

  const isBetween = (y: number, m: number, d: number) => {
    if (!customStart || !customEnd) return false;
    const c = new Date(y, m, d), s = parseDate(customStart), e = parseDate(customEnd);
    return c >= s && c <= e;
  };
  const isStart = (y: number, m: number, d: number) => {
    if (!customStart) return false;
    const s = parseDate(customStart);
    return s.getFullYear() === y && s.getMonth() === m && s.getDate() === d;
  };
  const isEnd = (y: number, m: number, d: number) => {
    if (!customEnd) return false;
    const e = parseDate(customEnd);
    return e.getFullYear() === y && e.getMonth() === m && e.getDate() === d;
  };

  return (
    <div className="border border-border rounded-card p-2.5 bg-surface">
      <div className="flex items-center justify-between mb-2">
        <button onClick={onPrev} aria-label="Previous month" className="p-1 rounded hover:bg-nav-hover text-text-muted hover:text-text-primary transition-colors">
          <ChevronLeft size={14} />
        </button>
        <span className="text-xs font-semibold text-text-primary">{monthName}</span>
        <button onClick={onNext} aria-label="Next month" className="p-1 rounded hover:bg-nav-hover text-text-muted hover:text-text-primary transition-colors">
          <ChevronRight size={14} />
        </button>
      </div>
      <div className="grid grid-cols-7 gap-0 mb-1">
        {WEEKDAYS.map((wd) => (
          <div key={wd} className="text-center text-[10px] font-medium text-text-muted py-1">{wd}</div>
        ))}
      </div>
      {weeks.map((week, wi) => (
        <div key={wi} className="grid grid-cols-7 gap-0">
          {week.map((day, di) => {
            if (day === null) return <div key={di} />;
            const between = isBetween(year, month, day);
            const s = isStart(year, month, day);
            const e = isEnd(year, month, day);
            return (
              <button
                key={di}
                onClick={() => onDayClick(year, month, day)}
                className={`h-7 text-[11px] rounded-md transition-colors
                  ${s || e ? "bg-accent text-white font-semibold" : ""}
                  ${between && !s && !e ? "bg-accent/10 text-accent" : ""}
                  ${!s && !e && !between ? "text-text-secondary hover:bg-nav-hover" : ""}`}
              >
                {day}
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}

// ── Main picker ─────────────────────────────────────────────────────────────
export default function DateRangePicker({ value, onChange }: DateRangePickerProps) {
  const [open, setOpen] = useState(false);
  const [customStart, setCustomStart] = useState(value.startDate);
  const [customEnd, setCustomEnd] = useState(value.endDate);
  const [activePreset, setActivePreset] = useState<string | null>(value.label);
  const [pickingEnd, setPickingEnd] = useState(false);

  const now = new Date();
  const [calMonth, setCalMonth] = useState({ year: now.getFullYear(), month: now.getMonth() });

  const popoverRef = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);

  const syncFromValue = useCallback(() => {
    setCustomStart(value.startDate);
    setCustomEnd(value.endDate);
    setActivePreset(value.label);
    setPickingEnd(false);
  }, [value]);

  useEffect(() => { syncFromValue(); }, [syncFromValue]);

  // Position popover with fixed + viewport clamp
  const positionPopover = useCallback(() => {
    if (!btnRef.current || !popoverRef.current) return;
    const btn = btnRef.current.getBoundingClientRect();
    const pop = popoverRef.current;
    const pw = pop.offsetWidth || 320;
    const ph = pop.offsetHeight || 420;
    const pad = 8;

    // Horizontal: prefer right-aligned, clamp to viewport
    let left = btn.right - pw;
    left = Math.max(pad, Math.min(left, window.innerWidth - pw - pad));
    pop.style.left = `${left}px`;
    pop.style.right = "auto";

    // Vertical: below if space, else above — clamp height to available space so presets never clip
    const spaceBelow = window.innerHeight - btn.bottom;
    const vh70 = window.innerHeight * 0.7;
    if (spaceBelow < ph + pad) {
      pop.style.top = "auto";
      pop.style.bottom = `${window.innerHeight - btn.top + 4}px`;
      pop.style.maxHeight = `${Math.min(vh70, btn.top - 16)}px`;
      pop.style.overflowY = "auto";
    } else {
      pop.style.top = `${btn.bottom + 4}px`;
      pop.style.bottom = "auto";
      pop.style.maxHeight = `${Math.min(vh70, window.innerHeight - btn.bottom - 16)}px`;
      pop.style.overflowY = "auto";
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    // rAF ensures offsetWidth is measured after render
    const id = requestAnimationFrame(positionPopover);
    window.addEventListener("resize", positionPopover);
    window.addEventListener("scroll", positionPopover, true);
    return () => {
      cancelAnimationFrame(id);
      window.removeEventListener("resize", positionPopover);
      window.removeEventListener("scroll", positionPopover, true);
    };
  }, [open, positionPopover]);

  const handlePreset = (preset: typeof PRESETS[0]) => {
    const { start, end } = preset.getRange();
    setCustomStart(start);
    setCustomEnd(end);
    setActivePreset(preset.label);
    setPickingEnd(false);
  };

  const handleApply = () => {
    if (customStart && customEnd && customStart <= customEnd) {
      onChange({ startDate: customStart, endDate: customEnd, label: activePreset || "Custom" });
      setOpen(false);
      setPickingEnd(false);
    }
  };

  const handleCancel = () => {
    syncFromValue();
    setOpen(false);
  };

  const handleDayClick = (y: number, m: number, d: number) => {
    const clicked = toISODate(new Date(y, m, d));
    setActivePreset(null);
    if (!pickingEnd) {
      // Begin (or restart) a range: set start + placeholder end
      setCustomStart(clicked);
      setCustomEnd(clicked);
      setPickingEnd(true);
    } else {
      // Finish the range with the end date (swap if inverted)
      if (clicked < customStart) {
        setCustomEnd(customStart);
        setCustomStart(clicked);
      } else {
        setCustomEnd(clicked);
      }
      setPickingEnd(false);
    }
  };

  const calPrev = () => setCalMonth((p) => {
    const d = new Date(p.year, p.month - 1, 1);
    return { year: d.getFullYear(), month: d.getMonth() };
  });
  const calNext = () => setCalMonth((p) => {
    const d = new Date(p.year, p.month + 1, 1);
    return { year: d.getFullYear(), month: d.getMonth() };
  });

  return (
    <div className="relative">
      <button
        ref={btnRef}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="dialog"
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-btn border border-border text-sm text-text-secondary hover:bg-nav-hover transition-colors"
      >
        <Calendar size={14} />
        <span>{value.label}</span>
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={handleCancel} aria-hidden />
          <div
            ref={popoverRef}
            role="dialog"
            aria-label="Select date range"
            className="fixed z-50 w-80 max-w-[calc(100vw-16px)] bg-surface border border-border rounded-card shadow-lg overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header — sticky so it stays visible when content scrolls */}
            <div className="sticky top-0 z-10 bg-surface flex items-center justify-between px-4 pt-3 pb-2 border-b border-divider">
              <span className="text-sm font-semibold text-text-primary">Select Date Range</span>
              <button
                onClick={handleCancel}
                aria-label="Close"
                className="p-1 rounded hover:bg-nav-hover text-text-muted hover:text-text-primary transition-colors"
              >
                <X size={14} />
              </button>
            </div>

            <div className="p-4 space-y-3">
              {/* Presets */}
              <div className="grid grid-cols-2 gap-1.5">
                {PRESETS.map((p) => (
                  <button
                    key={p.label}
                    onClick={() => handlePreset(p)}
                    className={`px-2 py-1.5 text-xs rounded-btn border transition-colors font-medium text-left
                      ${activePreset === p.label
                        ? "border-accent bg-accent/5 text-accent"
                        : "border-border text-text-secondary hover:border-accent/40 hover:text-accent"}`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>

              <div className="border-t border-divider" />

              {/* Start / End read-only displays */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[10px] font-medium text-text-muted mb-1">Start Date</label>
                  <div className="px-2.5 py-1.5 text-xs border border-border rounded-input bg-nav-hover text-text-primary truncate">
                    {customStart ? formatDisplay(customStart) : "Select"}
                  </div>
                </div>
                <div>
                  <label className="block text-[10px] font-medium text-text-muted mb-1">End Date</label>
                  <div className="px-2.5 py-1.5 text-xs border border-border rounded-input bg-nav-hover text-text-primary truncate">
                    {customEnd ? formatDisplay(customEnd) : "Select"}
                  </div>
                </div>
              </div>

              {/* Shared calendar */}
              <div className="mt-1">
                <MonthCalendar
                  year={calMonth.year} month={calMonth.month}
                  customStart={customStart} customEnd={customEnd}
                  onPrev={calPrev} onNext={calNext} onDayClick={handleDayClick}
                />
              </div>

              {/* Summary */}
              {customStart && customEnd && (
                <div className="text-xs text-text-secondary text-center py-1">
                  {formatDisplay(customStart)} → {formatDisplay(customEnd)}
                </div>
              )}

              {/* Footer */}
              <div className="flex items-center justify-end gap-2 pt-2 border-t border-divider">
                <button
                  onClick={handleCancel}
                  className="px-4 py-1.5 text-xs font-medium text-text-secondary border border-border rounded-btn hover:bg-nav-hover transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleApply}
                  disabled={!customStart || !customEnd || customStart > customEnd}
                  className="px-4 py-1.5 text-xs font-medium text-white bg-accent rounded-btn hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Apply
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
