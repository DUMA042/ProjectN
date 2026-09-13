import { useState, useMemo, useRef, useEffect } from "react";
import { Search, Check } from "lucide-react";

interface ColumnFilterDropdownProps {
  columnKey: string;
  header: string;
  uniqueValues: string[];
  selected: Set<string>;
  onApply: (columnKey: string, selected: Set<string>) => void;
  onClose: () => void;
}

export default function ColumnFilterDropdown({
  columnKey,
  header,
  uniqueValues,
  selected,
  onApply,
  onClose,
}: ColumnFilterDropdownProps) {
  const [search, setSearch] = useState("");
  const [localSelected, setLocalSelected] = useState<Set<string>>(new Set(selected));
  const containerRef = useRef<HTMLDivElement>(null);

  const filteredValues = useMemo(() => {
    if (!search.trim()) return uniqueValues;
    const q = search.toLowerCase();
    return uniqueValues.filter((v) => v.toLowerCase().includes(q));
  }, [uniqueValues, search]);

  const allFilteredSelected = filteredValues.length > 0 && filteredValues.every((v) => localSelected.has(v));

  const toggleValue = (val: string) => {
    setLocalSelected((prev) => {
      const next = new Set(prev);
      if (next.has(val)) next.delete(val);
      else next.add(val);
      return next;
    });
  };

  const toggleSelectAllFiltered = () => {
    if (allFilteredSelected) {
      setLocalSelected((prev) => {
        const next = new Set(prev);
        filteredValues.forEach((v) => next.delete(v));
        return next;
      });
    } else {
      setLocalSelected((prev) => {
        const next = new Set(prev);
        filteredValues.forEach((v) => next.add(v));
        return next;
      });
    }
  };

  const handleApply = () => {
    onApply(columnKey, localSelected);
    onClose();
  };

  const handleClear = () => {
    setLocalSelected(new Set());
  };

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  return (
    <div
      ref={containerRef}
      className="absolute left-0 top-full mt-1 z-30 w-56 bg-surface border border-border rounded-card shadow-lg overflow-hidden flex flex-col"
      style={{ maxHeight: "320px" }}
      onClick={(e) => e.stopPropagation()}
    >
      {/* Search */}
      <div className="p-2 border-b border-divider flex-shrink-0">
        <div className="relative">
          <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            autoFocus
            type="text"
            placeholder={`Search ${header.toLowerCase()}...`}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-7 pr-2 py-1.5 text-xs border border-border rounded-input bg-surface text-text-primary placeholder-text-muted focus:outline-none focus:border-accent"
          />
        </div>
      </div>

      {/* Select all */}
      <div className="px-2 py-1.5 border-b border-divider flex-shrink-0">
        <div
          role="checkbox"
          aria-checked={allFilteredSelected}
          onClick={toggleSelectAllFiltered}
          className="flex items-center gap-2 cursor-pointer group"
        >
          <div
            className={`w-3.5 h-3.5 rounded-[3px] border flex items-center justify-center flex-shrink-0 transition-colors
              ${allFilteredSelected ? "bg-accent border-accent" : "border-border group-hover:border-accent/40"}`}
          >
            {allFilteredSelected && <Check size={10} className="text-white" strokeWidth={3} />}
          </div>
          <span className="text-xs text-text-secondary group-hover:text-text-primary">
            {allFilteredSelected ? "Deselect all" : "Select all"}
            {search.trim() ? ` (${filteredValues.length})` : ""}
          </span>
        </div>
      </div>

      {/* Values list */}
      <div className="overflow-y-auto flex-1 min-h-0">
        {filteredValues.length === 0 ? (
          <p className="text-xs text-text-muted text-center py-6">No results</p>
        ) : (
          <div className="py-1">
            {filteredValues.map((val) => {
              const isSelected = localSelected.has(val);
              return (
                <div
                  key={val}
                  role="checkbox"
                  aria-checked={isSelected}
                  onClick={() => toggleValue(val)}
                  className="flex items-center gap-2 px-3 py-1.5 hover:bg-nav-hover cursor-pointer group"
                >
                  <div
                    className={`w-3.5 h-3.5 rounded-[3px] border flex items-center justify-center flex-shrink-0 transition-colors
                      ${isSelected ? "bg-accent border-accent" : "border-border group-hover:border-accent/40"}`}
                  >
                    {isSelected && <Check size={10} className="text-white" strokeWidth={3} />}
                  </div>
                  <span className="text-xs text-text-primary truncate flex-1" title={val}>
                    {val || "—"}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-2 py-2 border-t border-divider flex-shrink-0">
        <button
          onClick={handleClear}
          className="text-xs text-text-muted hover:text-text-primary px-2 py-1 rounded-btn hover:bg-nav-hover transition-colors"
        >
          Clear
        </button>
        <button
          onClick={handleApply}
          className="text-xs font-medium text-white bg-accent px-3 py-1 rounded-btn hover:opacity-90 transition-opacity"
        >
          Apply
        </button>
      </div>
    </div>
  );
}
