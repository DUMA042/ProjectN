import { useEffect, useRef, useState } from "react";
import { Plus } from "lucide-react";
import ColumnFilterDropdown from "@/components/ui/ColumnFilterDropdown";
import { useAnalyticsDimensions } from "@/hooks/useAnalytics";
import { useManagementScope } from "@/hooks/useManagementScope";

/** "＋ Filter" popover: pick a dimension, then multi-select its values. */
export default function FilterPopover() {
  const [open, setOpen] = useState(false);
  const [activeDim, setActiveDim] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  const { data: dims } = useAnalyticsDimensions();
  const { filters, setFilter } = useManagementScope();

  const attributeDims = (dims?.dimensions || []).filter(
    (d) => d.kind === "attribute" && d.key !== "location"
  );

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setActiveDim(null);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const activeMeta = attributeDims.find((d) => d.key === activeDim);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => { setOpen((v) => !v); setActiveDim(null); }}
        className={`flex items-center gap-1 px-2.5 py-1.5 text-xs border rounded-btn transition-colors ${
          open ? "border-accent text-accent bg-accent/5" : "border-border text-text-secondary hover:bg-nav-hover"
        }`}
      >
        <Plus size={12} /> Filter
      </button>

      {open && !activeMeta && (
        <div className="absolute left-0 top-full mt-1 z-30 w-48 bg-surface border border-border rounded-card shadow-lg overflow-hidden py-1 max-h-[300px] overflow-y-auto">
          <p className="px-3 py-1.5 text-[10px] uppercase tracking-wide text-text-muted">Filter by</p>
          {attributeDims.map((d) => {
            const active = (filters[d.key] || []).length;
            return (
              <button
                key={d.key}
                onClick={() => setActiveDim(d.key)}
                className="w-full flex items-center justify-between px-3 py-1.5 text-xs text-text-primary hover:bg-nav-hover text-left"
              >
                <span className="truncate">{d.label}</span>
                {active > 0 && (
                  <span className="text-[10px] font-semibold text-accent bg-accent/10 rounded-full px-1.5">
                    {active}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}

      {open && activeMeta && (
        <ColumnFilterDropdown
          columnKey={activeMeta.key}
          header={activeMeta.label}
          uniqueValues={(dims?.options?.[activeMeta.key] || []).map(String)}
          selected={new Set(filters[activeMeta.key] || [])}
          onApply={(key, selected) => { setFilter(key, [...selected]); setOpen(false); setActiveDim(null); }}
          onClose={() => { setOpen(false); setActiveDim(null); }}
        />
      )}
    </div>
  );
}
