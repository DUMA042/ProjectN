import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import { useManagementScope } from "@/hooks/useManagementScope";
import { useAnalyticsDimensions } from "@/hooks/useAnalytics";

/** Removable scope chips — double as the drill breadcrumb. */
export default function ScopeChips() {
  const { filters, removeFilter, removeDimension, clearFilters } = useManagementScope();
  const { data: dims } = useAnalyticsDimensions();

  const labelOf = (key: string) => {
    if (key === "location") return "Location";
    return dims?.dimensions.find((d) => d.key === key)?.label || key.replace(/_/g, " ");
  };

  const chips: { dim: string; value: string }[] = [];
  for (const [dim, values] of Object.entries(filters)) {
    values.forEach((v) => chips.push({ dim, value: v }));
  }

  if (chips.length === 0) return null;
  const count = chips.length;

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <AnimatePresence>
        {chips.map(({ dim, value }) => (
          <motion.button
            key={`${dim}:${value}`}
            layout
            initial={{ opacity: 0, scale: 0.85 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.85 }}
            transition={{ duration: 0.15 }}
            onClick={() => removeFilter(dim, value)}
            className="group flex items-center gap-1 pl-2 pr-1 py-0.5 text-[11px] bg-accent/5 border border-accent/30 text-accent rounded-full hover:bg-accent/10 transition-colors"
            title="Remove filter"
          >
            <span className="text-text-secondary">{labelOf(dim)}:</span>
            <span className="font-medium max-w-[140px] truncate">{value}</span>
            <X size={11} className="text-accent/60 group-hover:text-accent" />
          </motion.button>
        ))}
      </AnimatePresence>
      {count > 1 && (
        <button
          onClick={clearFilters}
          className="text-[11px] text-text-muted hover:text-danger px-1.5 py-0.5 rounded-btn hover:bg-nav-hover transition-colors"
        >
          Clear all ({count})
        </button>
      )}
    </div>
  );
}
