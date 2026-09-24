import { useState } from "react";
import { Filter, ChevronDown } from "lucide-react";
import ColumnFilterDropdown from "@/components/ui/ColumnFilterDropdown";

interface FilterDropdownProps {
  label: string;
  columnKey: string;
  options: string[];
  selected: Set<string>;
  onChange: (key: string, selected: Set<string>) => void;
}

export default function FilterDropdown({ label, columnKey, options, selected, onChange }: FilterDropdownProps) {
  const [open, setOpen] = useState(false);
  const count = selected.size;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs border rounded-btn transition-colors ${
          count > 0 ? "border-accent text-accent bg-accent/5" : "border-border text-text-secondary hover:bg-nav-hover"
        }`}
      >
        <Filter size={12} />
        {label}
        {count > 0 && (
          <span className="ml-0.5 px-1.5 py-0.5 rounded-full bg-accent text-white text-[10px] font-semibold">
            {count}
          </span>
        )}
        <ChevronDown size={12} />
      </button>
      {open && (
        <ColumnFilterDropdown
          columnKey={columnKey}
          header={label}
          uniqueValues={options}
          selected={selected}
          onApply={onChange}
          onClose={() => setOpen(false)}
        />
      )}
    </div>
  );
}
