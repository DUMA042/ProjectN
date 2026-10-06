import { useState } from "react";
import { AlertTriangle, ShieldCheck } from "lucide-react";
import type { HashMode } from "@/lib/reportBuild";

interface Props {
  files: { id: string; display_name: string; row_count: number }[];
  warning: string;
  busy: boolean;
  onConfirm: (mode: HashMode) => void;
  onCancel: () => void;
}

/** Hashing choice for individual files: names only, or names + IDs. */
export default function BuildHashDialog({ files, warning, busy, onConfirm, onCancel }: Props) {
  const [mode, setMode] = useState<HashMode>("names_only");
  return (
    <div className="fixed inset-0 z-[70] bg-black/40 flex items-center justify-center p-4" onClick={onCancel}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Hash sensitive information"
        className="card-container rounded-card p-5 w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 mb-1">
          <ShieldCheck size={16} className="text-accent flex-shrink-0" />
          <h3 className="text-sm font-semibold text-text-primary">Hash sensitive information</h3>
        </div>
        <p className="text-xs text-text-secondary mb-3">
          {files.length} individual file{files.length === 1 ? "" : "s"} detected:{" "}
          <span className="font-medium text-text-primary">
            {files.map((f) => f.display_name).join(", ")}
          </span>
          . Employee names and IDs in these files will be replaced with anonymous codes
          before anything is sent to the AI. Your original files stay unchanged.
        </p>
        <div className="space-y-2 mb-3">
          <label className="flex items-start gap-2 p-2.5 rounded-btn border border-border hover:bg-nav-hover cursor-pointer transition-colors">
            <input
              type="radio"
              name="hash-mode"
              checked={mode === "names_only"}
              onChange={() => setMode("names_only")}
              className="mt-0.5 accent-[#1677FF]"
            />
            <span>
              <span className="block text-sm font-medium text-text-primary">Hash names only</span>
              <span className="block text-xs text-text-secondary">
                Employee names are anonymized; IDs stay readable so ID-based grouping still works.
              </span>
            </span>
          </label>
          <label className="flex items-start gap-2 p-2.5 rounded-btn border border-border hover:bg-nav-hover cursor-pointer transition-colors">
            <input
              type="radio"
              name="hash-mode"
              checked={mode === "names_and_ids"}
              onChange={() => setMode("names_and_ids")}
              className="mt-0.5 accent-[#1677FF]"
            />
            <span>
              <span className="block text-sm font-medium text-text-primary">Hash names and IDs</span>
              <span className="block text-xs text-text-secondary">
                Both names and IDs are anonymized together for maximum privacy.
              </span>
            </span>
          </label>
        </div>
        {mode === "names_and_ids" && (
          <div className="flex items-start gap-2 mb-3 p-2.5 rounded-btn bg-badge-amber-bg text-xs text-badge-amber-text">
            <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
            <span>{warning}</span>
          </div>
        )}
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            disabled={busy}
            className="px-3 py-1.5 text-xs border border-border rounded-btn bg-surface text-text-secondary hover:bg-nav-hover transition-colors disabled:opacity-40"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(mode)}
            disabled={busy}
            className="px-3 py-1.5 text-xs font-medium text-white bg-accent rounded-btn hover:opacity-90 transition-opacity disabled:opacity-40"
          >
            {busy ? "Hashing…" : "Confirm and hash"}
          </button>
        </div>
      </div>
    </div>
  );
}
