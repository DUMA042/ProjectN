import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, Check, ChevronLeft } from "lucide-react";
import { useAnalyticsMetrics } from "@/hooks/useAnalytics";

export interface MetricMeta {
  key: string;
  domain: string;
  label: string;
  type: string;
  polarity?: string | null;
}

interface MetricPickerProps {
  /** Selected metric key(s). */
  value: string | string[];
  onChange: (key: string | string[]) => void;
  multi?: boolean;
  /** Restrict to these subject groups (domain keys). */
  domains?: string[];
  label?: string;
  className?: string;
}

const DOMAIN_LABELS: Record<string, string> = {
  attendance: "Attendance",
  leave: "Leave",
  training: "Training",
  employees: "Workforce",
};

const DOMAIN_ORDER = ["attendance", "leave", "training", "employees"];

/** Dropdown listing the unified metric catalog grouped by subject. */
export default function MetricPicker({ value, onChange, multi, domains, label, className = "" }: MetricPickerProps) {
  const { data } = useAnalyticsMetrics();
  const [open, setOpen] = useState(false);
  const [activeGroup, setActiveGroup] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  const metrics: MetricMeta[] = useMemo(() => data?.metrics || [], [data]);

  const groups = useMemo(() => {
    const filtered = domains ? metrics.filter((m) => domains.includes(m.domain)) : metrics;
    const byDomain = new Map<string, MetricMeta[]>();
    filtered.forEach((m) => {
      const list = byDomain.get(m.domain) || [];
      list.push(m);
      byDomain.set(m.domain, list);
    });
    return DOMAIN_ORDER
      .filter((d) => byDomain.has(d))
      .map((d) => ({ domain: d, label: DOMAIN_LABELS[d] || d, items: byDomain.get(d)! }));
  }, [metrics, domains]);

  const all: MetricMeta[] = useMemo(() => groups.flatMap((g) => g.items), [groups]);

  const currentLabel = useMemo(() => {
    if (multi && Array.isArray(value)) {
      if (value.length === 0) return "Metrics";
      const metas = value.map((k) => all.find((m) => m.key === k)).filter(Boolean) as MetricMeta[];
      if (metas.length === 1) return metas[0].label;
      if (metas.length === 2) return metas.map((m) => m.label).join(", ");
      // "Attendance rate +2 more" — a count alone reads like a bare number
      return `${metas[0].label} +${metas.length - 1} more`;
    }
    return all.find((m) => m.key === value)?.label || "Metric";
  }, [all, value, multi]);

  const currentTooltip = useMemo(() => {
    if (multi && Array.isArray(value)) {
      return value.map((k) => all.find((m) => m.key === k)?.label).filter(Boolean).join(", ") || undefined;
    }
    return undefined;
  }, [all, value, multi]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const pick = (m: MetricMeta) => {
    if (multi && Array.isArray(value)) {
      const next = value.includes(m.key) ? value.filter((k) => k !== m.key) : [...value, m.key];
      onChange(next);
    } else {
      onChange(m.key);
      setOpen(false);
    }
  };

  const shown = activeGroup ? groups.find((g) => g.domain === activeGroup)?.items || [] : all.flat();
  void shown;

  return (
    <div ref={ref} className={`relative ${className}`}>
      <button
        onClick={() => setOpen((v) => !v)}
        title={currentTooltip}
        className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs border rounded-btn transition-colors ${
          open ? "border-accent text-accent bg-accent/5" : "border-border text-text-secondary hover:bg-nav-hover"
        }`}
      >
        {label && <span className="text-text-muted">{label}</span>}
        <span className="font-medium text-text-primary">{currentLabel}</span>
        <ChevronDown size={12} className={open ? "rotate-180 transition-transform" : "transition-transform"} />
      </button>

      {open && (
        <div
          className="absolute right-0 top-full mt-1 z-30 w-64 bg-surface border border-border rounded-card shadow-lg overflow-hidden flex flex-col"
          style={{ maxHeight: 340 }}
        >
          {activeGroup ? (
            <>
              <button
                onClick={() => setActiveGroup(null)}
                className="flex items-center gap-1 px-3 py-2 text-xs font-semibold text-text-primary border-b border-divider hover:bg-nav-hover"
              >
                <ChevronLeft size={12} /> {DOMAIN_LABELS[activeGroup] || activeGroup}
              </button>
              <div className="overflow-y-auto">
                {(groups.find((g) => g.domain === activeGroup)?.items || []).map((m) => (
                  <MetricRow key={m.key} m={m} selected={Array.isArray(value) ? value.includes(m.key) : value === m.key} onClick={() => pick(m)} />
                ))}
              </div>
            </>
          ) : (
            <div className="overflow-y-auto py-1">
              {multi && (
                <p className="px-3 pb-1 text-[10px] text-text-muted">
                  Select multiple — each becomes a column. ✓ marks what's shown.
                </p>
              )}
              {groups.map((g) => (
                <div key={g.domain}>
                  <button
                    onClick={() => setActiveGroup(g.domain)}
                    className="w-full flex items-center justify-between px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-text-muted hover:bg-nav-hover"
                  >
                    {g.label}
                    <span className="text-[10px] font-normal normal-case">{g.items.length} metrics</span>
                  </button>
                  {/* show top items inline for quick access */}
                  {g.items.slice(0, 3).map((m) => (
                    <MetricRow key={m.key} m={m} selected={Array.isArray(value) ? value.includes(m.key) : value === m.key} onClick={() => pick(m)} />
                  ))}
                  {g.items.length > 3 && (
                    <button
                      onClick={() => setActiveGroup(g.domain)}
                      className="w-full text-left px-3 pb-1.5 text-[11px] text-accent hover:underline"
                    >
                      +{g.items.length - 3} more…
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function MetricRow({ m, selected, onClick }: { m: MetricMeta; selected: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-2 px-3 py-1.5 text-left text-xs hover:bg-nav-hover ${selected ? "text-accent font-medium" : "text-text-primary"}`}
    >
      <span className={`w-3.5 flex-shrink-0 ${selected ? "" : "opacity-0"}`}>
        <Check size={13} strokeWidth={3} />
      </span>
      <span className="truncate flex-1">{m.label}</span>
      {m.type === "pct" && <span className="text-[10px] text-text-muted">%</span>}
    </button>
  );
}
