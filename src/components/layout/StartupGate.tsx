import { Loader2, ServerCrash } from "lucide-react";

interface StartupGateProps {
  phase: "starting" | "failed";
  message?: string;
  onRetry?: () => void;
  onClose?: () => void;
}

const LOG_LOCATION = "%APPDATA%\\Flow\\logs\\startup.log";

export default function StartupGate({
  phase,
  message,
  onRetry,
  onClose,
}: StartupGateProps) {
  return (
    <div className="flex h-screen w-screen items-center justify-center bg-canvas p-6">
      <div className="w-full max-w-md text-center space-y-4">
        <p className="text-2xl font-semibold text-text-primary">Flow</p>

        {phase === "starting" ? (
          <>
            <Loader2 size={28} className="mx-auto animate-spin text-accent" />
            <p role="status" className="text-sm text-text-secondary">
              Starting the local service…
            </p>
            <p className="text-xs text-text-muted">
              The first launch prepares the database and can take up to a minute.
            </p>
          </>
        ) : (
          <>
            <ServerCrash size={28} className="mx-auto text-danger" />
            <p className="text-sm font-semibold text-text-primary">
              Flow could not start.
            </p>
            <p role="alert" className="text-xs text-text-secondary">
              {message || "The local service did not become ready."}
            </p>
            <p className="text-[11px] text-text-muted break-all">
              Logs: {LOG_LOCATION}
            </p>
            <div className="flex justify-center gap-2 pt-1">
              {onRetry && (
                <button
                  onClick={onRetry}
                  className="px-4 py-2 text-xs font-medium text-white bg-accent rounded-btn hover:opacity-90 transition-opacity"
                >
                  Retry
                </button>
              )}
              {onClose && (
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-xs border border-border rounded-btn text-text-secondary hover:bg-nav-hover transition-colors"
                >
                  Close
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
