interface PercentCountToggleProps {
  value: "pct" | "count";
  onChange: (mode: "pct" | "count") => void;
}

export default function PercentCountToggle({ value, onChange }: PercentCountToggleProps) {
  return (
    <div
      className="flex items-center gap-0.5 bg-nav-hover rounded-btn p-0.5 flex-shrink-0"
      role="group"
      aria-label="Display metric as percentage or count"
    >
      <button
        onClick={() => onChange("pct")}
        title="Percentages"
        aria-pressed={value === "pct"}
        className={`px-2 py-1 text-xs font-semibold rounded-[5px] transition-all ${
          value === "pct"
            ? "bg-surface text-accent shadow-sm"
            : "text-text-secondary hover:text-text-primary"
        }`}
      >
        %
      </button>
      <button
        onClick={() => onChange("count")}
        title="Numbers"
        aria-pressed={value === "count"}
        className={`px-2 py-1 text-xs font-semibold rounded-[5px] transition-all ${
          value === "count"
            ? "bg-surface text-accent shadow-sm"
            : "text-text-secondary hover:text-text-primary"
        }`}
      >
        #
      </button>
    </div>
  );
}
