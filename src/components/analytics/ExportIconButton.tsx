import { Download } from "lucide-react";

/** Standard per-card CSV export icon button. */
export default function ExportIconButton({ onExport, title = "Export CSV" }: { onExport: () => void; title?: string }) {
  return (
    <button
      onClick={onExport}
      title={title}
      aria-label={title}
      className="p-2 rounded-btn text-text-muted hover:text-accent hover:bg-nav-hover transition-colors flex-shrink-0"
    >
      <Download size={14} />
    </button>
  );
}
