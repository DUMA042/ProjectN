import { motion } from "framer-motion";
import { Check, Loader2, AlertTriangle, XCircle } from "lucide-react";

type StepStatus = "pending" | "active" | "done" | "error";

interface Step {
  key: string;
  label: string;
  status: StepStatus;
}

interface ProcessTrackerProps {
  filename: string;
  steps: Step[];
  progress?: number;
  successCount?: number;
  failedCount?: number;
  onViewFailures?: () => void;
  errorMessage?: string;
  quarantineReason?: string;
}

const stepIcons: Record<StepStatus, React.ReactNode> = {
  pending: <span className="w-4 h-4 rounded-full border-2 border-text-muted" />,
  active: <Loader2 size={16} className="text-info animate-spin" />,
  done: <Check size={16} className="text-success" />,
  error: <XCircle size={16} className="text-danger" />,
};

export default function ProcessTracker({
  filename,
  steps,
  progress,
  successCount,
  failedCount,
  onViewFailures,
  errorMessage,
  quarantineReason,
}: ProcessTrackerProps) {
  const isDone = steps.every((s) => s.status === "done");
  const hasFailed = steps.some((s) => s.status === "error");
  const isQuarantined = !!quarantineReason;

  return (
    <motion.div
      className="card-container p-4"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="flex items-center gap-2 mb-3">
        <span className="text-sm font-semibold text-text-primary truncate">
          {filename}
        </span>
        {isDone && !hasFailed && (
          <span className="text-xs px-1.5 py-0.5 rounded-full bg-badge-green-bg text-badge-green-text font-medium">
            Complete
          </span>
        )}
        {isQuarantined && (
          <span className="text-xs px-1.5 py-0.5 rounded-full bg-[#FEF3C7] text-badge-amber-text font-medium">
            Quarantined
          </span>
        )}
      </div>

      {/* Steps */}
      <div className="space-y-1.5 mb-2">
        {steps.map((step, i) => (
          <motion.div
            key={step.key}
            className="flex items-center gap-2 text-xs"
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.08 }}
          >
            {stepIcons[step.status]}
            <span
              className={
                step.status === "done"
                  ? "text-success font-medium"
                  : step.status === "active"
                  ? "text-info font-medium"
                  : step.status === "error"
                  ? "text-danger"
                  : "text-text-muted"
              }
            >
              {step.label}
            </span>
          </motion.div>
        ))}
      </div>

      {/* Progress bar */}
      {progress !== undefined && progress > 0 && progress < 100 && (
        <div className="w-full h-2 bg-nav-hover rounded-full overflow-hidden mb-2">
          <motion.div
            className="h-full bg-info rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
      )}

      {/* Success/fail summary */}
      {isDone && (
        <div className="flex items-center gap-3 text-xs mt-1">
          {successCount !== undefined && (
            <span className="text-success font-medium">
              ✅ {successCount.toLocaleString()} success
            </span>
          )}
          {failedCount !== undefined && failedCount > 0 && (
            <button
              onClick={onViewFailures}
              className="text-danger font-medium hover:underline cursor-pointer"
            >
              ❌ {failedCount.toLocaleString()} failed — view details
            </button>
          )}
          {failedCount === 0 && !hasFailed && (
            <span className="text-text-muted">No failures</span>
          )}
        </div>
      )}

      {/* Error message */}
      {errorMessage && (
        <div className="flex items-start gap-2 mt-2 p-2 rounded-btn bg-[#FEF2F2] text-xs text-danger">
          <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Quarantine reason */}
      {quarantineReason && (
        <div className="flex items-start gap-2 mt-2 p-2 rounded-btn bg-[#FEF3C7] text-xs text-[#D97706]">
          <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
          <span>{quarantineReason}</span>
        </div>
      )}
    </motion.div>
  );
}
