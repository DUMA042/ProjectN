import { motion } from "framer-motion";
import { Clock, Download } from "lucide-react";
import DateRangePicker from "@/components/ui/DateRangePicker";
import { exportToCSV } from "@/lib/csvExport";
import type { DateRange } from "@/components/ui/DateRangePicker";

interface CheckinEntry {
  id_no: string;
  full_name: string;
  department: string;
  swipe_time: string;
  appearances?: number;
}

export type CheckinMode = "avg_checkin" | "top_arrivals";

interface EarliestCheckinsCardProps {
  title: string;
  data: CheckinEntry[];
  dateRange: DateRange;
  onDateChange: (range: DateRange) => void;
  limit: number;
  onLimitChange: (n: number) => void;
  loading?: boolean;
  isFetching?: boolean;
  mode?: CheckinMode;
  onModeChange?: (mode: CheckinMode) => void;
}

const medalStyles = [
  "bg-[#FEF3C7] text-[#D97706]",
  "bg-[#F1F5F9] text-[#64748B]",
  "bg-[#FEF2F2] text-[#DC2626]",
  "bg-[#F8FAFC] text-[#94A3B8]",
];

const LIMIT_OPTIONS = [5, 10, 15, 20, 25, 50];

const MODE_OPTIONS: { value: CheckinMode; label: string }[] = [
  { value: "avg_checkin", label: "Avg Check-in" },
  { value: "top_arrivals", label: "Top Arrivals" },
];

function ModeToggle({ mode, onModeChange }: { mode: CheckinMode; onModeChange?: (m: CheckinMode) => void }) {
  return (
    <div className="flex items-center gap-1 bg-nav-hover rounded-btn p-0.5 flex-shrink-0">
      {MODE_OPTIONS.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onModeChange?.(opt.value)}
          className={`flex-1 px-3 py-1 text-xs font-medium rounded-[5px] transition-all ${
            mode === opt.value
              ? "bg-surface text-accent shadow-sm"
              : "text-text-secondary hover:text-text-primary"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

export default function EarliestCheckinsCard({
  title,
  data,
  dateRange,
  onDateChange,
  limit,
  onLimitChange,
  loading,
  isFetching,
  mode = "avg_checkin",
  onModeChange,
}: EarliestCheckinsCardProps) {
  if (loading) {
    return (
      <div className="card-container p-5 animate-pulse h-[440px]">
        <div className="flex justify-between mb-4">
          <div className="h-5 w-40 bg-nav-hover rounded" />
          <div className="flex gap-2">
            <div className="h-8 w-24 bg-nav-hover rounded-btn" />
            <div className="h-8 w-14 bg-nav-hover rounded-btn" />
          </div>
        </div>
        {[...Array(6)].map((_, i) => (
          <div key={i} className="flex items-center gap-3 py-2">
            <div className="w-6 h-6 bg-nav-hover rounded-full" />
            <div className="flex-1"><div className="h-4 w-32 bg-nav-hover rounded mb-1" /><div className="h-3 w-20 bg-nav-hover rounded" /></div>
            <div className="h-5 w-14 bg-nav-hover rounded-full" />
          </div>
        ))}
      </div>
    );
  }

  if (!data.length) {
    return (
      <div className="card-container p-5 h-[440px] flex flex-col">
        <div className="flex items-center justify-between mb-3 flex-shrink-0 flex-wrap gap-2">
          <div>
            <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
            <p className="text-xs text-text-secondary mt-0.5">First swipe times</p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => exportToCSV(data, "earliest_check_ins", dateRange)}
              title="Export CSV"
              aria-label="Export CSV"
              className="p-2 rounded-btn text-text-muted hover:text-accent hover:bg-nav-hover transition-colors"
            >
              <Download size={14} />
            </button>
            <DateRangePicker value={dateRange} onChange={onDateChange} />
            <select
              value={limit}
              onChange={(e) => onLimitChange(Number(e.target.value))}
              className="px-2 py-1.5 text-xs border border-border rounded-btn bg-surface text-text-secondary cursor-pointer hover:bg-nav-hover"
            >
              {LIMIT_OPTIONS.map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>
        </div>
        <ModeToggle mode={mode} onModeChange={onModeChange} />
        <div className="flex flex-col items-center justify-center flex-1 text-text-muted mt-3">
          <Clock size={36} strokeWidth={1.5} />
          <p className="text-sm mt-3 font-medium">No check-ins recorded</p>
          <p className="text-xs mt-1">for this date range</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card-container p-5 h-[440px] flex flex-col">
      <div className="flex items-center justify-between mb-3 flex-shrink-0 flex-wrap gap-2">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
          <p className="text-xs text-text-secondary mt-0.5">
            {mode === "top_arrivals" ? "Most frequent early arrivals" : "Top earliest swipe times"}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => exportToCSV(data, "earliest_check_ins", dateRange)}
            title="Export CSV"
            aria-label="Export CSV"
            className="p-2 rounded-btn text-text-muted hover:text-accent hover:bg-nav-hover transition-colors"
          >
            <Download size={14} />
          </button>
          <DateRangePicker value={dateRange} onChange={onDateChange} />
          <select
            value={limit}
            onChange={(e) => onLimitChange(Number(e.target.value))}
            className="px-2 py-1.5 text-xs border border-border rounded-btn bg-surface text-text-secondary cursor-pointer hover:bg-nav-hover"
          >
            {LIMIT_OPTIONS.map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>
      </div>

      <ModeToggle mode={mode} onModeChange={onModeChange} />

      <div className={`overflow-y-auto flex-1 min-h-0 space-y-1 pr-1.5 custom-scrollbar mt-3 transition-opacity ${isFetching ? "opacity-50" : "opacity-100"}`}>
        {data.slice(0, limit).map((entry, i) => (
          <motion.div
            key={`${entry.id_no}-${i}`}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: Math.min(i * 0.02, 0.2), duration: 0.15 }}
            className="flex items-center gap-2.5 py-2 px-2.5 rounded-lg hover:bg-nav-hover transition-colors cursor-default group"
          >
            <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${medalStyles[i] || medalStyles[3]}`}>
              {i + 1}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-[13px] font-medium text-text-primary truncate group-hover:text-accent transition-colors">
                {entry.full_name}
              </p>
              <p className="text-[11px] text-text-secondary truncate">{entry.department}</p>
            </div>
            {mode === "top_arrivals" && entry.appearances != null ? (
              <span className="text-[11px] font-mono font-semibold bg-[#DBEAFE] text-[#2563EB] px-2.5 py-0.5 rounded-full whitespace-nowrap flex-shrink-0">
                {entry.appearances}×
              </span>
            ) : (
              <span className="text-[11px] font-mono font-semibold bg-[#D1FAE5] text-[#059669] px-2.5 py-0.5 rounded-full whitespace-nowrap flex-shrink-0">
                {entry.swipe_time}
              </span>
            )}
          </motion.div>
        ))}
      </div>
    </div>
  );
}
