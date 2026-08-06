import { useState } from "react";
import { Calendar, ChevronDown } from "lucide-react";

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
  return d.toISOString().split("T")[0];
}

const PRESETS: { label: string; getRange: () => { start: string; end: string } }[] = [
  {
    label: "Today",
    getRange: () => {
      const d = toISODate(new Date());
      return { start: d, end: d };
    },
  },
  {
    label: "Yesterday",
    getRange: () => {
      const d = new Date();
      d.setDate(d.getDate() - 1);
      const v = toISODate(d);
      return { start: v, end: v };
    },
  },
  {
    label: "This Week",
    getRange: () => {
      const now = new Date();
      const day = now.getDay();
      const monday = new Date(now);
      monday.setDate(now.getDate() - ((day + 6) % 7));
      return { start: toISODate(monday), end: toISODate(now) };
    },
  },
  {
    label: "This Month",
    getRange: () => {
      const now = new Date();
      return {
        start: toISODate(new Date(now.getFullYear(), now.getMonth(), 1)),
        end: toISODate(now),
      };
    },
  },
  {
    label: "Last Month",
    getRange: () => {
      const now = new Date();
      const first = new Date(now.getFullYear(), now.getMonth() - 1, 1);
      const last = new Date(now.getFullYear(), now.getMonth(), 0);
      return { start: toISODate(first), end: toISODate(last) };
    },
  },
];

export default function DateRangePicker({ value, onChange }: DateRangePickerProps) {
  const [open, setOpen] = useState(false);
  const [customStart, setCustomStart] = useState(value.startDate);
  const [customEnd, setCustomEnd] = useState(value.endDate);

  const handlePreset = (preset: (typeof PRESETS)[0]) => {
    const { start, end } = preset.getRange();
    const range: DateRange = { startDate: start, endDate: end, label: preset.label };
    onChange(range);
    setOpen(false);
  };

  const handleCustom = () => {
    if (customStart && customEnd && customStart <= customEnd) {
      onChange({ startDate: customStart, endDate: customEnd, label: "Custom" });
      setOpen(false);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-btn border border-border text-sm text-text-secondary hover:bg-nav-hover transition-colors"
      >
        <Calendar size={14} />
        <span>{value.label}</span>
        <ChevronDown size={12} />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-20 w-52 bg-surface border border-border rounded-card shadow-subtle p-2 space-y-1">
            {PRESETS.map((p) => (
              <button
                key={p.label}
                onClick={() => handlePreset(p)}
                className={`w-full text-left px-3 py-2 rounded-btn text-sm transition-colors ${
                  value.label === p.label
                    ? "bg-nav-hover text-text-primary font-medium"
                    : "text-text-secondary hover:bg-nav-hover"
                }`}
              >
                {p.label}
              </button>
            ))}
            <div className="border-t border-divider pt-2 mt-1">
              <div className="flex gap-2 items-center">
                <input
                  type="date"
                  value={customStart}
                  onChange={(e) => setCustomStart(e.target.value)}
                  className="w-full px-2 py-1 text-xs border border-border rounded-input bg-surface text-text-primary"
                />
                <span className="text-text-muted text-xs">→</span>
                <input
                  type="date"
                  value={customEnd}
                  onChange={(e) => setCustomEnd(e.target.value)}
                  className="w-full px-2 py-1 text-xs border border-border rounded-input bg-surface text-text-primary"
                />
              </div>
              <button
                onClick={handleCustom}
                className="w-full mt-1 px-3 py-1.5 text-xs font-medium text-surface bg-accent rounded-btn hover:opacity-90 transition-opacity"
              >
                Apply Custom
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
