import { useAnalyticsToday } from "@/hooks/useAnalytics";
import WaffleChart from "./WaffleChart";
import { STATUS_COLORS, STATUS_LABELS } from "@/lib/analyticsColors";
import { fmtNum } from "@/lib/format";
import { CalendarCheck } from "lucide-react";

interface TodayCardProps {
  filters: Record<string, string[]>;
}

/** Live-ish today board: swipes, late-so-far, leave, training, no-swipe. */
export default function TodayCard({ filters }: TodayCardProps) {
  const { data, isLoading } = useAnalyticsToday(filters);

  const dateLabel = data
    ? new Date(`${data.date}T00:00:00`).toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" })
    : "";

  const waffle = data
    ? [
        { name: STATUS_LABELS.present, value: Math.max(0, data.swipers - (data.late_so_far ?? 0)), color: STATUS_COLORS.present },
        { name: STATUS_LABELS.late, value: data.late_so_far ?? 0, color: STATUS_COLORS.late },
        { name: STATUS_LABELS.leave, value: data.on_leave, color: STATUS_COLORS.leave },
        { name: STATUS_LABELS.training, value: data.in_training, color: STATUS_COLORS.training },
      ]
    : [];
  if (data?.no_swipe_yet != null && data.no_swipe_yet > 0) {
    waffle.push({ name: "No swipe yet", value: data.no_swipe_yet, color: "#E2E8F0" });
  }

  return (
    <div className="card-container p-4 flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <CalendarCheck size={14} className="text-accent" />
          <h4 className="text-xs font-semibold text-text-primary">Today</h4>
        </div>
        <span className="text-[11px] text-text-muted">{dateLabel}</span>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <div className="h-8 bg-nav-hover rounded animate-pulse" />
          <div className="h-24 bg-nav-hover rounded animate-pulse" />
        </div>
      ) : !data ? (
        <p className="text-xs text-text-muted">Today data unavailable.</p>
      ) : !data.is_working_day ? (
        <div>
          <p className="text-sm text-text-primary font-medium">Non-working day</p>
          <p className="text-xs text-text-secondary mt-1">
            {fmtNum(data.total_swipes)} swipe{data.total_swipes === 1 ? "" : "s"} recorded
            {data.on_leave > 0 && ` · ${fmtNum(data.on_leave)} on leave`}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-end gap-4">
            <div>
              <p className="text-2xl font-bold text-text-primary tabular-nums leading-none">{fmtNum(data.total_swipes)}</p>
              <p className="text-[11px] text-text-muted mt-1">swipes · {fmtNum(data.swipers)} people in</p>
            </div>
            {data.late_so_far != null && (
              <div>
                <p className="text-lg font-semibold text-warning tabular-nums leading-none">{fmtNum(data.late_so_far)}</p>
                <p className="text-[11px] text-text-muted mt-1">late so far</p>
              </div>
            )}
            {data.last_swipe && (
              <div className="ml-auto text-right">
                <p className="text-sm font-semibold text-text-primary tabular-nums">
                  {new Date(data.last_swipe).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}
                </p>
                <p className="text-[11px] text-text-muted">last swipe</p>
              </div>
            )}
          </div>
          {waffle.length > 0 && <WaffleChart parts={waffle} dotSize={8} />}
        </div>
      )}
    </div>
  );
}
