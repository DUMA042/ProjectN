import { AlertTriangle, ArrowRight } from "lucide-react";
import ExportIconButton from "./ExportIconButton";

export interface AttentionFlag {
  label: string;
  detail: string;
  tone?: "danger" | "warning" | "info";
  onClick?: () => void;
}

const TONE: Record<string, string> = {
  danger: "text-danger",
  warning: "text-warning",
  info: "text-info",
};

export default function AttentionFlags({ flags, loading, onExport }: { flags: AttentionFlag[]; loading?: boolean; onExport?: () => void }) {
  return (
    <div className="card-container p-4">
      <div className="flex items-center justify-between gap-2 mb-3">
        <h4 className="text-xs font-semibold text-text-primary">Attention</h4>
        {onExport && <ExportIconButton onExport={onExport} />}
      </div>
      {loading ? (
        <div className="space-y-2">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-8 bg-nav-hover rounded animate-pulse" />
          ))}
        </div>
      ) : flags.length === 0 ? (
        <p className="text-xs text-text-muted">Nothing flagged in the current scope.</p>
      ) : (
        <div className="space-y-1">
          {flags.map((f, i) => (
            <button
              key={i}
              onClick={f.onClick}
              disabled={!f.onClick}
              className={`w-full flex items-start gap-2 text-left px-2 py-1.5 rounded-btn transition-colors ${
                f.onClick ? "hover:bg-nav-hover" : "cursor-default"
              }`}
            >
              <AlertTriangle size={14} className={`mt-0.5 flex-shrink-0 ${TONE[f.tone || "warning"]}`} />
              <span className="flex-1 min-w-0">
                <span className="block text-xs font-medium text-text-primary truncate">{f.label}</span>
                <span className="block text-[11px] text-text-secondary truncate">{f.detail}</span>
              </span>
              {f.onClick && <ArrowRight size={13} className="text-text-muted mt-0.5 flex-shrink-0" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
