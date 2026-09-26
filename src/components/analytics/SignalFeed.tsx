import { motion, AnimatePresence } from "framer-motion";
import { ArrowUpRight, ArrowDownRight, CircleDot, ChevronRight } from "lucide-react";
import type { Signal } from "@/hooks/useAnalytics";

const SEVERITY_STYLE: Record<Signal["severity"], { icon: React.ReactNode; chip: string }> = {
  danger: {
    icon: <ArrowUpRight size={14} />,
    chip: "bg-badge-red-bg text-badge-red-text",
  },
  warning: {
    icon: <ArrowDownRight size={14} />,
    chip: "bg-badge-amber-bg text-badge-amber-text",
  },
  info: {
    icon: <CircleDot size={12} />,
    chip: "bg-nav-hover text-text-secondary",
  },
};

interface SignalFeedProps {
  signals: Signal[];
  loading: boolean;
  onDrill: (dimension: string, value: string) => void;
  onOpenEmployee: (id: string) => void;
}

/** Ranked auto-insights — each row carries the filter that diagnoses it. */
export default function SignalFeed({ signals, loading, onDrill, onOpenEmployee }: SignalFeedProps) {
  return (
    <div className="card-container p-4 flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-semibold text-text-primary">Signals</h4>
        <span className="text-[10px] text-text-muted uppercase tracking-wide">auto-detected · current vs previous</span>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-10 bg-nav-hover rounded animate-pulse" />
          ))}
        </div>
      ) : signals.length === 0 ? (
        <div className="flex-1 flex items-center justify-center py-8">
          <p className="text-xs text-text-muted text-center">
            All quiet — no notable movements in the current scope.
          </p>
        </div>
      ) : (
        <div className="space-y-1">
          <AnimatePresence initial={false}>
            {signals.map((s, i) => {
              const style = SEVERITY_STYLE[s.severity] || SEVERITY_STYLE.info;
              const isEmployee = s.drill.dimension === "employee_id";
              const good = s.good === true;
              const Icon = s.direction === "down" ? ArrowDownRight : ArrowUpRight;
              return (
                <motion.button
                  key={`${s.domain}:${s.metric}:${s.drill.dimension}:${s.drill.value}:${i}`}
                  layout
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04, duration: 0.2 }}
                  onClick={() => (isEmployee ? onOpenEmployee(String(s.drill.value)) : onDrill(s.drill.dimension, s.drill.value))}
                  className={`w-full flex items-start gap-2.5 text-left px-2 py-2 rounded-btn transition-colors hover:bg-nav-hover group`}
                >
                  <span
                    className={`mt-0.5 flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center ${style.chip}`}
                  >
                    {s.severity === "info" ? <CircleDot size={12} /> : <Icon size={13} className={good ? "rotate-180" : ""} />}
                  </span>
                  <span className="flex-1 min-w-0">
                    <span className="block text-xs text-text-primary leading-snug">{s.headline}</span>
                    <span className="block text-[11px] text-text-muted mt-0.5 truncate">{s.detail}</span>
                  </span>
                  <ChevronRight size={13} className="text-text-muted mt-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                </motion.button>
              );
            })}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
