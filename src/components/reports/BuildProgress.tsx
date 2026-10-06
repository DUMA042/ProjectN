import { motion } from "framer-motion";
import { Loader2, X } from "lucide-react";
import ProcessTracker from "@/components/ui/ProcessTracker";
import { BUILD_STAGES, buildStageLabel, type BuildJob } from "@/lib/reportBuild";

type StepStatus = "pending" | "active" | "done" | "error";

interface Props {
  job: BuildJob;
  names: Map<string, string>;
  /** File id -> classification ("individual" shows the Hashing step). */
  classifications: Map<string, string>;
  cancellable?: boolean;
  onCancel?: () => void;
}

function stepsFor(
  fileState: string,
  individual: boolean
): { label: string; status: StepStatus }[] {
  const labels = individual ? ["Inspected", "Hashed", "Validated"] : ["Inspected", "Ready"];
  const at = (i: number): StepStatus => {
    if (fileState === "done") return "done";
    if (fileState === "error") return i === 0 ? "done" : "error";
    if (fileState === "active") return i === 0 ? "done" : i === 1 ? "active" : "pending";
    return "pending";
  };
  return labels.map((label, i) => ({ label, status: at(i) }));
}

/** Overall stage line + per-file trackers (Upload-page design language). */
export default function BuildProgress({ job, names, classifications, cancellable, onCancel }: Props) {
  const stageIdx = BUILD_STAGES.indexOf(job.stage as (typeof BUILD_STAGES)[number]);
  const running = stageIdx >= 0 && job.stage !== "complete" && job.stage !== "cancelled";
  return (
    <div className="card-container overflow-hidden">
      <div className="px-4 pt-3 pb-2">
        <div className="flex items-center gap-2">
          {running && <Loader2 size={13} className="text-info animate-spin" />}
          <h2 className="text-xs font-semibold text-text-primary">
            {buildStageLabel(job.stage)}
          </h2>
          {cancellable && onCancel && (
            <button
              onClick={onCancel}
              title="Cancel this build"
              className="ml-auto px-2.5 py-1 text-[11px] border border-border rounded-btn bg-surface text-text-secondary hover:text-danger hover:bg-nav-hover transition-colors inline-flex items-center gap-1"
            >
              <X size={12} /> Cancel build
            </button>
          )}
        </div>
        {job.stage_detail && (
          <p className="text-[11px] text-text-muted mt-0.5">{job.stage_detail}</p>
        )}
        {running && (
          <div className="w-full h-1.5 bg-nav-hover rounded-full overflow-hidden mt-2">
            <motion.div
              className="h-full w-1/3 bg-info rounded-full"
              animate={{ x: ["-100%", "300%"] }}
              transition={{ repeat: Infinity, duration: 1.2, ease: "linear" }}
            />
          </div>
        )}
      </div>
      <div className="px-4 pb-3 space-y-2">
        {job.files.map((f) => (
          <ProcessTracker
            key={f.id}
            filename={names.get(f.id) || f.id}
            steps={stepsFor(f.state, classifications.get(f.id) === "individual").map((s) => ({
              key: s.label,
              label: s.label,
              status: s.status,
            }))}
            errorMessage={f.error || undefined}
          />
        ))}
      </div>
    </div>
  );
}
