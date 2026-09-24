interface GroupByBarProps {
  dimensions: { key: string; label: string }[];
  selected: string[];
  onToggle: (key: string) => void;
  max?: number;
}

export default function GroupByBar({ dimensions, selected, onToggle, max = 2 }: GroupByBarProps) {
  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <span className="text-[11px] text-text-muted mr-1">Group by:</span>
      {dimensions.map((d) => {
        const active = selected.includes(d.key);
        const disabled = !active && selected.length >= max;
        return (
          <button
            key={d.key}
            onClick={() => !disabled && onToggle(d.key)}
            disabled={disabled}
            className={`px-2 py-1 text-[11px] rounded-btn border transition-colors ${
              active
                ? "border-accent text-accent bg-accent/5"
                : disabled
                  ? "border-border text-text-muted opacity-50 cursor-not-allowed"
                  : "border-border text-text-secondary hover:border-accent/40 hover:text-accent"
            }`}
          >
            {d.label}
          </button>
        );
      })}
    </div>
  );
}
