import { useEffect, useRef } from "react";
import ProcessTracker from "@/components/ui/ProcessTracker";
import { useIngestionStatus } from "@/hooks/useIngestion";
import type { UploadResult } from "@/hooks/useIngestion";

interface IngestionTrackerCardProps {
  result: UploadResult;
  onViewDetails: (filename: string, id: string | null) => void;
  onCompleted: (filename: string, rowsLoaded: number) => void;
  onQuarantined: (filename: string, reason: string) => void;
  onFailed: (filename: string, message: string) => void;
  onDismiss: () => void;
}

export default function IngestionTrackerCard({
  result,
  onViewDetails,
  onCompleted,
  onQuarantined,
  onFailed,
  onDismiss,
}: IngestionTrackerCardProps) {
  const enabled = !!result.ingestion_id && result.status !== "classification_failed";
  const { data: status } = useIngestionStatus(result.ingestion_id, enabled);

  const filename = result.normalized_filename || result.original_filename;
  const dbStatus = status?.db_status || result.status;
  const ctx = status?.error_context || {};

  const steps = buildSteps(dbStatus);
  const isQuarantined = dbStatus === "quarantined";
  const isDone = dbStatus === "completed" || dbStatus === "failed" || isQuarantined;

  // Extract totals from error_context
  let successCount: number | undefined;
  let failedCount: number | undefined;
  const loadResults = ctx.load_results || {};
  if (typeof loadResults === "object" && !Array.isArray(loadResults)) {
    successCount = 0;
    failedCount = 0;
    for (const v of Object.values(loadResults)) {
      if (typeof v === "object" && v !== null && "success" in v) {
        successCount += (v as any).success || 0;
        failedCount += (v as any).failed || 0;
      }
    }
  }
  if (ctx.total_successes !== undefined) successCount = ctx.total_successes;
  if (ctx.total_failures !== undefined) failedCount = ctx.total_failures;

  // Fire one-time notifications when a terminal state is reached
  const notifiedRef = useRef(false);
  useEffect(() => {
    if (!isDone || notifiedRef.current) return;
    notifiedRef.current = true;
    if (dbStatus === "completed") {
      onCompleted(filename, successCount ?? 0);
    } else if (isQuarantined) {
      onQuarantined(filename, ctx.reason || "Unknown reason");
    } else if (dbStatus === "failed") {
      onFailed(filename, ctx.fatal_error || "Processing failed");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isDone]);

  const stageInfo = status?.stage_info;

  return (
    <ProcessTracker
      filename={filename}
      steps={steps}
      stageLabel={stageInfo?.label}
      percent={stageInfo?.percent}
      current={stageInfo?.current}
      total={stageInfo?.total}
      successCount={isDone && !hasFailures(steps) ? successCount : undefined}
      failedCount={isDone ? failedCount : undefined}
      onViewDetails={() => onViewDetails(filename, result.ingestion_id)}
      errorMessage={dbStatus === "failed" ? ctx.fatal_error : undefined}
      quarantineReason={isQuarantined ? ctx.reason : undefined}
      dismissible={isDone}
      onDismiss={onDismiss}
    />
  );
}

function hasFailures(steps: { status: string }[]): boolean {
  return steps.some((s) => s.status === "error");
}

function buildSteps(dbStatus: string): { key: string; label: string; status: "pending" | "active" | "done" | "error" }[] {
  const base: { key: string; label: string; status: "pending" | "active" | "done" | "error" }[] = [
    { key: "received", label: "Received", status: "done" },
    { key: "routed", label: "Routed", status: "done" },
    { key: "processing", label: "Processing", status: "pending" },
    { key: "done", label: "Done", status: "pending" },
  ];

  if (dbStatus === "pending") {
    base[1].status = "done";
    base[2].status = "pending";
    base[2].label = "Waiting…";
    return base;
  }

  if (dbStatus === "processing") {
    base[2].status = "active";
    return base;
  }

  if (dbStatus === "completed") {
    base[2].status = "done";
    base[3].status = "done";
    return base;
  }

  if (dbStatus === "failed") {
    base[2].status = "error";
    base[2].label = "Failed";
    base[3].status = "error";
    return base;
  }

  if (dbStatus === "quarantined") {
    base[1].status = "error";
    base[2].status = "error";
    base[2].label = "Quarantined";
    return [base[0], base[1], base[2]];
  }

  if (dbStatus === "classification_failed") {
    base[0].status = "done";
    base[1].status = "error";
    base[1].label = "Classify fail";
    return base.slice(0, 2);
  }

  base[2].status = "active";
  return base;
}
