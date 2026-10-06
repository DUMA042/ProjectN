import { AlertTriangle } from "lucide-react";

interface Props {
  title: string;
  message: string;
  confirmLabel?: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/** In-app delete confirmation card (replaces window.confirm). */
export default function ConfirmCard({
  title,
  message,
  confirmLabel = "Delete",
  busy = false,
  onConfirm,
  onCancel,
}: Props) {
  return (
    <div className="fixed inset-0 z-[70] bg-black/40 flex items-center justify-center p-4" onClick={onCancel}>
      <div
        role="alertdialog"
        aria-modal="true"
        aria-label={title}
        className="card-container rounded-card p-5 w-full max-w-sm"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 mb-2">
          <span className="w-7 h-7 rounded-full bg-badge-amber-bg flex items-center justify-center flex-shrink-0">
            <AlertTriangle size={15} className="text-badge-amber-text" />
          </span>
          <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
        </div>
        <p className="text-xs text-text-secondary mb-4">{message}</p>
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            disabled={busy}
            className="px-3 py-1.5 text-xs border border-border rounded-btn bg-surface text-text-secondary hover:bg-nav-hover transition-colors disabled:opacity-40"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={busy}
            className="px-3 py-1.5 text-xs font-medium text-white bg-danger rounded-btn hover:opacity-90 transition-opacity disabled:opacity-40"
          >
            {busy ? "Deleting…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
