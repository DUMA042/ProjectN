import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";

interface KpiCardProps {
  title: string;
  value: number;
  trend?: number;
  icon: LucideIcon;
  sparklineData?: number[];
  loading?: boolean;
}

function CountUp({ end, duration = 1.5 }: { end: number; duration?: number }) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (end === 0) {
      setCount(0);
      return;
    }
    let startTime: number | null = null;
    let frame: number;

    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const elapsed = timestamp - startTime;
      const progress = Math.min(elapsed / (duration * 1000), 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.floor(eased * end));
      if (progress < 1) {
        frame = requestAnimationFrame(animate);
      }
    };

    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [end, duration]);

  return <>{count.toLocaleString()}</>;
}

export default function KpiCard({
  title,
  value,
  trend,
  icon: Icon,
  sparklineData,
  loading,
}: KpiCardProps) {
  if (loading) {
    return (
      <div className="card-container p-4 animate-pulse">
        <div className="h-4 w-24 bg-nav-hover rounded mb-2" />
        <div className="h-8 w-20 bg-nav-hover rounded mb-2" />
        <div className="h-4 w-14 bg-nav-hover rounded" />
      </div>
    );
  }

  const trendAbsent = trend === undefined || trend === null;

  return (
    <motion.div
      className="card-container rounded-card p-4"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="flex justify-between items-start mb-2">
        <span className="text-sm text-text-secondary font-medium">
          {title}
        </span>
        <Icon size={20} className="text-text-muted" strokeWidth={1.75} />
      </div>

      <div className="kpi-value mb-2">
        <CountUp end={value} />
      </div>

      <div className="flex items-center gap-2">
        {!trendAbsent && (
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded-full ${
              trend >= 0
                ? "bg-badge-green-bg text-badge-green-text"
                : "bg-badge-red-bg text-badge-red-text"
            }`}
          >
            {trend >= 0 ? "+" : ""}
            {trend}%
          </span>
        )}

        {sparklineData && sparklineData.length > 0 && (
          <svg
            className="flex-1 h-8"
            viewBox={`0 0 ${sparklineData.length} 20`}
            preserveAspectRatio="none"
          >
            <polyline
              fill="none"
              stroke={trend && trend >= 0 ? "#10B981" : "#64748B"}
              strokeWidth="1.5"
              points={sparklineData
                .map(
                  (v, i) =>
                    `${i},${20 - (v / Math.max(...sparklineData)) * 18}`
                )
                .join(" ")}
            />
          </svg>
        )}
      </div>
    </motion.div>
  );
}
