import { motion } from "framer-motion";
import { RefreshCw, Clock } from "lucide-react";

interface LeaderboardEntry {
  swipe_time: string;
  full_name: string;
  department: string;
  id_no: string;
}

interface LeaderboardCardProps {
  title: string;
  data: LeaderboardEntry[];
  loading?: boolean;
  onRefresh?: () => void;
}

const medalStyles = [
  "bg-[#FEF3C7] text-[#D97706]",   // Gold
  "bg-[#F1F5F9] text-[#64748B]",    // Silver
  "bg-[#FEF2F2] text-[#DC2626]",    // Bronze
  "bg-[#F8FAFC] text-[#94A3B8]",    // Neutral
];

export default function LeaderboardCard({
  title,
  data,
  loading,
  onRefresh,
}: LeaderboardCardProps) {
  if (loading) {
    return (
      <div className="card-container p-5 animate-pulse">
        <div className="flex justify-between mb-4">
          <div className="h-5 w-48 bg-nav-hover rounded" />
          <div className="h-8 w-8 bg-nav-hover rounded" />
        </div>
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex items-center gap-3 py-2.5">
            <div className="w-6 h-6 bg-nav-hover rounded-full" />
            <div className="flex-1">
              <div className="h-4 w-32 bg-nav-hover rounded mb-1" />
              <div className="h-3 w-20 bg-nav-hover rounded" />
            </div>
            <div className="h-5 w-16 bg-nav-hover rounded-full" />
          </div>
        ))}
      </div>
    );
  }

  if (!data.length) {
    return (
      <div className="card-container p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-4">{title}</h3>
        <div className="flex flex-col items-center justify-center py-12 text-text-muted">
          <Clock size={36} strokeWidth={1.5} />
          <p className="text-sm mt-3">No check-ins recorded today</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card-container p-5 h-full">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="p-1.5 rounded-btn hover:bg-nav-hover transition-colors text-text-muted hover:text-text-secondary"
          >
            <RefreshCw size={16} />
          </button>
        )}
      </div>

      <div className="space-y-0.5">
        {data.map((entry, i) => (
          <motion.div
            key={entry.id_no}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05, duration: 0.2 }}
            className="flex items-center gap-3 py-2.5 px-2 rounded-lg hover:bg-nav-hover transition-colors cursor-default group"
          >
            <span
              className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                medalStyles[i] || medalStyles[3]
              }`}
            >
              {i + 1}
            </span>

            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text-primary truncate group-hover:text-accent transition-colors">
                {entry.full_name}
              </p>
              <p className="text-xs text-text-secondary">{entry.department}</p>
            </div>

            <span className="text-xs font-mono font-medium bg-[#D1FAE5] text-[#059669] px-2.5 py-1 rounded-full whitespace-nowrap">
              {entry.swipe_time}
            </span>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
