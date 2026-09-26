import { MapPin, ChevronDown } from "lucide-react";
import { useAnalyticsDimensions } from "@/hooks/useAnalytics";

interface LocationSelectProps {
  value: string | null;
  onChange: (location: string | null) => void;
}

/** Page-wide location scope — All Locations + every location in the system. */
export default function LocationSelect({ value, onChange }: LocationSelectProps) {
  const { data } = useAnalyticsDimensions();
  const options = (data?.options?.location || []).filter(Boolean).sort((a, b) => a.localeCompare(b));

  return (
    <div className="relative flex items-center">
      <MapPin size={13} className="absolute left-2.5 text-text-muted pointer-events-none" />
      <select
        value={value || ""}
        onChange={(e) => onChange(e.target.value || null)}
        className="appearance-none pl-7 pr-7 py-1.5 text-xs border border-border rounded-btn bg-surface text-text-primary font-medium hover:bg-nav-hover cursor-pointer focus:outline-none focus:border-accent max-w-[180px]"
        title="Scope every card on this page to one location"
      >
        <option value="">All Locations</option>
        {options.map((loc) => (
          <option key={loc} value={loc}>{loc}</option>
        ))}
      </select>
      <ChevronDown size={12} className="absolute right-2 text-text-muted pointer-events-none" />
    </div>
  );
}
