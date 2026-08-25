import { motion } from "framer-motion";
import {
  Check, Loader2, AlertTriangle, XCircle,
  FileSpreadsheet, X,
} from "lucide-react";

type StepStatus = "pending" | "active" | "done" | "error";

interface Step {
  key: string;
  label: string;
  status: StepStatus;
}

interface ProcessTrackerProps {
  filename: string;
  steps: Step[];
  stageLabel?: string;
  percent?: number | null;
  current?: number | null;
  total?: number | null;
  successCount?: number;
  failedCount?: number;
  onViewDetails?: () => void;
  errorMessage?: string;
  quarantineReason?: string;
  dismissible?: boolean;
  onDismiss?: () => void;
}

const stepIcons: Record<StepStatus, React.ReactNode> = {
  pending: <span className="w-3.5 h-3.5 rounded-full border-2 border-text-muted inline-block" />,
  active: <Loader2 size={15} className="text-info animate-spin" />,
  done: <Check size={15} className="text-success" />,
  error: <XCircle size={15} className="text-danger" />,
};

export default function ProcessTracker({
  filename,
  steps,
  stageLabel,
  percent,
  current,
  total,
  successCount,
  failedCount,
  onViewDetails,
  errorMessage,
  quarantineReason,
  dismissible,
  onDismiss,
}: ProcessTrackerProps) {
  const isDone = steps.every((s) => s.status === "done");
  const hasFailed = steps.some((s) => s.status === "error");
  const isQuarantined = !!quarantineReason;
  const isProcessing = steps.some((s) => s.status === "active");

  return (
    <motion.div
      className="card-container rounded-card p-4"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <FileSpreadsheet size={16} className="text-success flex-shrink-0" />
        <span className="text-sm font-semibold text-text-primary truncate flex-1">
          {filename}
        </span>
        {isDone && !hasFailed && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-badge-green-bg text-badge-green-text font-medium flex-shrink-0">
            Complete
          </span>
        )}
        {isQuarantined && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-badge-amber-bg text-badge-amber-text font-medium flex-shrink-0">
            Quarantined
          </span>
        )}
        {dismissible && (
          <button
            onClick={onDismiss}
            className="p-1 rounded-btn hover:bg-nav-hover text-text-muted hover:text-text-secondary transition-colors flex-shrink-0"
            title="Dismiss"
          >
            <X size={14} />
          </button>
        )}
      </div>

      {/* Horizontal stepper */}
      <div className="flex items-center mb-3">
        {steps.map((step, i) => (
          <div key={step.key} className="flex items-center flex-1 last:flex-none">
            <div className="flex flex-col items-center gap-1">
              {stepIcons[step.status]}
              <span
                className={`text-[10px] whitespace-nowrap ${
                  step.status === "done"
                    ? "text-success font-medium"
                    : step.status === "active"
                    ? "text-info font-medium"
                    : step.status === "error"
                    ? "text-danger font-medium"
                    : "text-text-muted"
                }`}
              >
                {step.label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div
                className={`flex-1 h-px mx-1 mb-4 transition-colors duration-300 ${
                  step.status === "done" ? "bg-success" : "bg-border"
                }`}
              />
            )}
          </div>
        ))}
      </div>

      {/* Stage label + progress */}
      {(isProcessing || (percent !== undefined && percent !== null && percent > 0 && percent < 100)) && (
        <div className="mb-2">
          {stageLabel && (
            <p className="text-xs text-text-secondary mb-1">{stageLabel}</p>
          )}
          <div className="w-full h-1.5 bg-nav-hover rounded-full overflow-hidden">
            {percent !== undefined && percent !== null ? (
              <motion.div
                className="h-full bg-info rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${percent}%` }}
                transition={{ duration: 0.3 }}
              />
            ) : (
              <motion.div
                className="h-full w-1/3 bg-info rounded-full"
                animate={{ x: ["-100%", "300%"] }}
                transition={{ repeat: Infinity, duration: 1.2, ease: "linear" }}
              />
            )}
          </div>
        </div>
      )}

      {/* Success/fail summary */}
      {isDone && !hasFailed && !isQuarantined && (
        <div className="flex items-center gap-3 text-xs mt-1">
          {successCount !== undefined && (
            <span className="text-success font-medium">
              ✅ {successCount.toLocaleString()} rows added
            </span>
          )}
          {failedCount !== undefined && failedCount > 0 && (
            <button
              onClick={onViewDetails}
              className="text-danger font-medium hover:underline cursor-pointer"
            >
              ❌ {failedCount.toLocaleString()} failed — view details
            </button>
          )}
          {failedCount === 0 && (
            <span className="text-text-muted">No failures</span>
          )}
          {onViewDetails && (
            <button
              onClick={onViewDetails}
              className="ml-auto text-info hover:underline cursor-pointer"
            >
              View details
            </button>
          )}
        </div>
      )}

      {/* Error message */}
      {errorMessage && (
        <div className="flex items-start gap-2 mt-2 p-2 rounded-btn bg-badge-red-bg text-xs text-danger">
          <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Quarantine reason */}
      {quarantineReason && (
        <div className="flex items-start gap-2 mt-2 p-2 rounded-btn bg-badge-amber-bg text-xs text-badge-amber-text">
          <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
          <span>{quarantineReason}</span>
        </div>
      )}

      {/* Details link for quarantined/failed too */}
      {(isQuarantined || hasFailed) && onViewDetails && (
        <button onClick={onViewDetails} className="mt-1 text-xs text-info hover:underline">
          View details
        </button>
      )}
    </motion.div>
  );
}
