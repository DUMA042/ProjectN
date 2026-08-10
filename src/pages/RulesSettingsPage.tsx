import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Save, RotateCcw, Plus, X, ToggleLeft, ToggleRight } from "lucide-react";
import { useRules, useUpdateRule, useSeedRules } from "@/hooks/useRules";

const DAYS = [
  { key: "monday", label: "Monday" },
  { key: "tuesday", label: "Tuesday" },
  { key: "wednesday", label: "Wednesday" },
  { key: "thursday", label: "Thursday" },
  { key: "friday", label: "Friday" },
  { key: "saturday", label: "Saturday" },
  { key: "sunday", label: "Sunday" },
];

interface TimeFields {
  early_before: string;
  normal_start: string;
  normal_end: string;
  late_after: string;
}

interface DayWorkingHours {
  checkin: TimeFields;
  checkout: TimeFields;
}

const defaultTimes: TimeFields = {
  early_before: "08:30",
  normal_start: "08:30",
  normal_end: "09:00",
  late_after: "09:00",
};

const defaultCheckoutMonThu: TimeFields = {
  early_before: "17:00",
  normal_start: "17:00",
  normal_end: "18:00",
  late_after: "18:00",
};

const defaultCheckoutFri: TimeFields = {
  early_before: "16:00",
  normal_start: "16:00",
  normal_end: "17:00",
  late_after: "17:00",
};

export default function RulesSettingsPage() {
  const { data: rules, isLoading } = useRules();
  const updateRule = useUpdateRule();
  const seedRules = useSeedRules();

  const [workingHours, setWorkingHours] = useState<Record<string, DayWorkingHours | null>>({});
  const [incompleteHours, setIncompleteHours] = useState(1);
  const [holidays, setHolidays] = useState<string[]>([]);
  const [newHoliday, setNewHoliday] = useState("");
  const [eligibleStatuses, setEligibleStatuses] = useState<string[]>(["Active"]);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!rules) return;
    setWorkingHours(rules["working_hours"] || {});
    setIncompleteHours(rules["incomplete_threshold"]?.hours ?? 1);
    setHolidays(rules["holidays"]?.dates ?? []);
    setEligibleStatuses(rules["eligible_statuses"]?.statuses ?? ["Active"]);
  }, [rules]);

  const toggleDay = (day: string) => {
    const current = workingHours[day];
    if (current === null) {
      const isFri = day === "friday";
      setWorkingHours((prev) => ({
        ...prev,
        [day]: {
          checkin: { ...defaultTimes },
          checkout: isFri ? { ...defaultCheckoutFri } : { ...defaultCheckoutMonThu },
        },
      }));
    } else {
      setWorkingHours((prev) => ({ ...prev, [day]: null }));
    }
  };

  const updateDayTime = (
    day: string,
    category: "checkin" | "checkout",
    field: keyof TimeFields,
    value: string
  ) => {
    setWorkingHours((prev) => {
      const current = prev[day];
      if (!current) return prev;
      return {
        ...prev,
        [day]: {
          ...current,
          [category]: { ...current[category], [field]: value },
        },
      };
    });
  };

  const addHoliday = () => {
    if (newHoliday && !holidays.includes(newHoliday)) {
      setHolidays((prev) => [...prev, newHoliday].sort());
      setNewHoliday("");
    }
  };

  const removeHoliday = (date: string) => {
    setHolidays((prev) => prev.filter((d) => d !== date));
  };

  const handleSaveAll = async () => {
    try {
      await updateRule.mutateAsync({ key: "working_hours", value: workingHours });
      await updateRule.mutateAsync({ key: "incomplete_threshold", value: { hours: incompleteHours } });
      await updateRule.mutateAsync({ key: "holidays", value: { dates: holidays } });
      await updateRule.mutateAsync({ key: "eligible_statuses", value: { statuses: eligibleStatuses } });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {}
  };

  const handleReset = async () => {
    await seedRules.mutateAsync();
  };

  const TimeInputRow = ({
    category,
    day,
    times,
  }: {
    category: "checkin" | "checkout";
    day: string;
    times: TimeFields;
  }) => (
    <div className="flex items-center gap-2 text-xs text-text-secondary ml-2 mb-1">
      <span className="w-16 font-medium capitalize">{category}:</span>
      <span className="w-10">Early</span>
      <input
        type="time"
        value={times.early_before}
        onChange={(e) => updateDayTime(day, category, "early_before", e.target.value)}
        className="w-24 px-2 py-1 border border-border rounded-input bg-surface text-text-primary text-xs"
      />
      <span className="w-12 text-center">Normal</span>
      <input
        type="time"
        value={times.normal_start}
        onChange={(e) => updateDayTime(day, category, "normal_start", e.target.value)}
        className="w-24 px-2 py-1 border border-border rounded-input bg-surface text-text-primary text-xs"
      />
      <span className="text-text-muted">–</span>
      <input
        type="time"
        value={times.normal_end}
        onChange={(e) => updateDayTime(day, category, "normal_end", e.target.value)}
        className="w-24 px-2 py-1 border border-border rounded-input bg-surface text-text-primary text-xs"
      />
      <span className="w-8 text-center">Late</span>
      <input
        type="time"
        value={times.late_after}
        onChange={(e) => updateDayTime(day, category, "late_after", e.target.value)}
        className="w-24 px-2 py-1 border border-border rounded-input bg-surface text-text-primary text-xs"
      />
    </div>
  );

  if (isLoading) {
    return (
      <div className="p-6 space-y-5 animate-pulse">
        <div className="h-7 w-48 bg-nav-hover rounded" />
        <div className="h-[400px] bg-nav-hover rounded-card" />
      </div>
    );
  }

  return (
    <motion.div
      className="p-6 space-y-5 max-w-3xl"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Rules Settings</h1>
          <p className="text-sm text-text-secondary mt-0.5">
            Configure business rules for attendance calculations
          </p>
        </div>
      </div>

      {/* Per-Day Working Hours */}
      <div className="card-container p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-4">
          Per-Day Working Hours
        </h3>
        <div className="space-y-1">
          {DAYS.map((day) => {
            const dayRules = workingHours[day.key];
            const isActive = dayRules !== null && dayRules !== undefined;

            return (
              <div
                key={day.key}
                className={`rounded-card border p-3 transition-colors ${
                  isActive ? "border-border" : "border-divider bg-nav-hover/50"
                }`}
              >
                <div className="flex items-center gap-3 mb-2">
                  <button
                    onClick={() => toggleDay(day.key)}
                    className={`flex items-center gap-2 transition-colors ${
                      isActive ? "text-success" : "text-text-muted"
                    }`}
                  >
                    {isActive ? <ToggleRight size={18} /> : <ToggleLeft size={18} />}
                    <span className="text-sm font-medium">{day.label}</span>
                  </button>
                  {isActive ? (
                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-badge-green-bg text-badge-green-text font-medium">
                      Working
                    </span>
                  ) : (
                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-nav-hover text-text-muted font-medium">
                      Non-working
                    </span>
                  )}
                </div>

                {isActive && dayRules && (
                  <div className="pl-8">
                    <TimeInputRow
                      category="checkin"
                      day={day.key}
                      times={dayRules.checkin}
                    />
                    <TimeInputRow
                      category="checkout"
                      day={day.key}
                      times={dayRules.checkout}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Incomplete Day */}
      <div className="card-container p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-4">
          Incomplete Work Day Threshold
        </h3>
        <div className="flex items-center gap-3">
          <span className="text-sm text-text-secondary">
            Mark as incomplete if total work time is less than
          </span>
          <input
            type="number"
            min={0.5}
            max={8}
            step={0.5}
            value={incompleteHours}
            onChange={(e) => setIncompleteHours(Number(e.target.value))}
            className="w-20 px-2 py-1 border border-border rounded-input bg-surface text-text-primary text-sm text-center"
          />
          <span className="text-sm text-text-secondary">hour(s)</span>
        </div>
      </div>

      {/* Holidays */}
      <div className="card-container p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-4">Holidays</h3>
        <div className="flex flex-wrap gap-2 mb-3">
          {holidays.map((date) => (
            <span
              key={date}
              className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-nav-hover text-text-primary font-medium"
            >
              {date}
              <button onClick={() => removeHoliday(date)} className="text-text-muted hover:text-danger transition-colors">
                <X size={12} />
              </button>
            </span>
          ))}
          {holidays.length === 0 && (
            <span className="text-xs text-text-muted">No holidays configured</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={newHoliday}
            onChange={(e) => setNewHoliday(e.target.value)}
            className="px-3 py-1.5 border border-border rounded-input bg-surface text-text-primary text-sm"
          />
          <button
            onClick={addHoliday}
            className="flex items-center gap-1 px-3 py-1.5 text-sm border border-border rounded-btn text-text-secondary hover:bg-nav-hover transition-colors"
          >
            <Plus size={14} />
            Add
          </button>
        </div>
      </div>

      {/* Eligible Statuses */}
      <div className="card-container p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-4">
          Eligible Statuses
        </h3>
        <p className="text-xs text-text-secondary mb-3">
          Employees with these statuses are considered active for attendance
        </p>
        <div className="flex flex-wrap gap-2">
          {eligibleStatuses.map((status, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-nav-hover text-text-primary font-medium"
            >
              {status}
              <button
                onClick={() =>
                  setEligibleStatuses((prev) => prev.filter((_, j) => j !== i))
                }
                className="text-text-muted hover:text-danger transition-colors"
              >
                <X size={12} />
              </button>
            </span>
          ))}
          <button
            onClick={() => {
              const name = prompt("Enter status name:");
              if (name && name.trim() && !eligibleStatuses.includes(name.trim())) {
                setEligibleStatuses((prev) => [...prev, name.trim()]);
              }
            }}
            className="flex items-center gap-1 px-3 py-1 text-xs border border-dashed border-text-muted rounded-full text-text-muted hover:text-text-secondary hover:border-text-secondary transition-colors"
          >
            <Plus size={12} />
            Add status
          </button>
        </div>
      </div>
      {/* Footer */}
      <div className="card-container p-4 flex items-center justify-between">
        <p className="text-xs text-text-muted">
          Changes take effect immediately for all future calculations.
        </p>
        <div className="flex items-center gap-2">
          <button
            onClick={handleReset}
            className="px-4 py-2 text-sm border border-border rounded-btn text-text-secondary hover:bg-nav-hover transition-colors"
          >
            Reset Defaults
          </button>
          <button
            onClick={handleSaveAll}
            disabled={updateRule.isPending}
            className={`px-5 py-2 text-sm rounded-btn text-white font-medium transition-colors ${
              saved ? "bg-success" : "bg-accent hover:bg-accent-hover"
            }`}
          >
            {saved ? "Saved!" : "Save All"}
          </button>
        </div>
      </div>
    </motion.div>
  );
}
