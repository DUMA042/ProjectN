import { useEffect, useRef, useState } from "react";
import { Star, ChevronDown, Trash2, Check } from "lucide-react";
import { useManagementScope } from "@/hooks/useManagementScope";

/** Saved scope views — persist {tab, location, range, compare, filters}. */
export default function SavedViewsMenu() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [justSaved, setJustSaved] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const { savedViews, saveView, applyView, deleteView } = useManagementScope();

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const handleSave = () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    saveView(trimmed);
    setName("");
    setJustSaved(true);
    setTimeout(() => setJustSaved(false), 1500);
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs border rounded-btn transition-colors ${
          open ? "border-accent text-accent bg-accent/5" : "border-border text-text-secondary hover:bg-nav-hover"
        }`}
        title="Save or restore scope views"
      >
        <Star size={12} className={savedViews.length > 0 ? "text-warning fill-warning" : ""} />
        Views
        {savedViews.length > 0 && (
          <span className="text-[10px] font-semibold text-accent">{savedViews.length}</span>
        )}
        <ChevronDown size={11} className={open ? "rotate-180 transition-transform" : "transition-transform"} />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 z-30 w-72 bg-surface border border-border rounded-card shadow-lg overflow-hidden">
          <div className="p-2.5 border-b border-divider">
            <p className="text-[10px] uppercase tracking-wide text-text-muted mb-1.5">Save current scope</p>
            <div className="flex items-center gap-1.5">
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSave()}
                placeholder="View name (e.g. Finance Q3)"
                className="flex-1 min-w-0 px-2 py-1.5 text-xs border border-border rounded-input bg-surface text-text-primary placeholder-text-muted focus:outline-none focus:border-accent"
              />
              <button
                onClick={handleSave}
                disabled={!name.trim()}
                className={`px-2.5 py-1.5 text-xs font-medium rounded-btn transition-colors ${
                  name.trim()
                    ? "text-white bg-accent hover:opacity-90"
                    : "text-text-muted bg-nav-hover cursor-not-allowed"
                }`}
              >
                {justSaved ? <Check size={12} /> : "Save"}
              </button>
            </div>
          </div>

          <div className="max-h-[220px] overflow-y-auto">
            {savedViews.length === 0 ? (
              <p className="text-xs text-text-muted text-center py-4">
                No saved views yet — scope the page, then save it here.
              </p>
            ) : (
              [...savedViews].reverse().map((v) => (
                <div key={v.name} className="flex items-center gap-1 px-2 py-1.5 hover:bg-nav-hover group">
                  <button
                    onClick={() => { applyView(v.name); setOpen(false); }}
                    className="flex-1 min-w-0 text-left"
                  >
                    <p className="text-xs font-medium text-text-primary truncate">{v.name}</p>
                    <p className="text-[10px] text-text-muted truncate">
                      {v.dateRange.label}
                      {v.location ? ` · ${v.location}` : " · All Locations"}
                      {Object.keys(v.filters).length > 0 ? ` · ${Object.values(v.filters).flat().length} filter(s)` : ""}
                    </p>
                  </button>
                  <button
                    onClick={() => deleteView(v.name)}
                    className="p-1 text-text-muted hover:text-danger opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Delete view"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
