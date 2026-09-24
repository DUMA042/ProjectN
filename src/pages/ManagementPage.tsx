import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { RefreshCw, Download, X } from "lucide-react";
import DateRangePicker from "@/components/ui/DateRangePicker";
import type { DateRange } from "@/components/ui/DateRangePicker";
import SegmentedControl from "@/components/analytics/SegmentedControl";
import FilterDropdown from "@/components/analytics/FilterDropdown";
import OverviewTab from "@/pages/management/OverviewTab";
import EmployeesTab from "@/pages/management/EmployeesTab";
import AttendanceTab from "@/pages/management/AttendanceTab";
import EmployeeDetailDrawer from "@/components/ui/EmployeeDetailDrawer";
import { useAnalyticsDimensions, useAnalyticsRefresh, toApiFilters } from "@/hooks/useAnalytics";

type Tab = "overview" | "employees" | "attendance" | "leave" | "training";

const TABS: { value: Tab; label: string }[] = [
  { value: "overview", label: "Overview" },
  { value: "employees", label: "Employees" },
  { value: "attendance", label: "Attendance" },
  { value: "leave", label: "Leave" },
  { value: "training", label: "Training" },
];

const FILTER_DIMENSIONS = [
  "location", "department", "grade_level", "rank", "employment_type", "status", "sex", "zone",
];

function defaultRange(): DateRange {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 89);
  const iso = (d: Date) => d.toISOString().split("T")[0];
  return { startDate: iso(start), endDate: iso(end), label: "Last 90 Days" };
}

export default function ManagementPage() {
  const [tab, setTab] = useState<Tab>("overview");
  const [dateRange, setDateRange] = useState<DateRange>(defaultRange());
  const [compare, setCompare] = useState(false);
  const [filters, setFilters] = useState<Record<string, Set<string>>>({});
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string | null>(null);

  const { data: dims } = useAnalyticsDimensions();
  const refresh = useAnalyticsRefresh();

  const dimensionOptions = dims?.options || {};
  const apiFilters = useMemo(() => toApiFilters(filters), [filters]);
  const dateRangeObj = useMemo(
    () => ({ start: dateRange.startDate, end: dateRange.endDate }),
    [dateRange.startDate, dateRange.endDate]
  );

  const setFilter = (key: string, selected: Set<string>) => {
    setFilters((prev) => {
      const next = { ...prev };
      if (selected.size === 0) delete next[key];
      else next[key] = selected;
      return next;
    });
  };

  const drill = (dimension: string, value: string) => {
    setFilters((prev) => {
      const cur = new Set(prev[dimension] || []);
      cur.add(value);
      return { ...prev, [dimension]: cur };
    });
  };

  const activeFilterCount = Object.values(filters).reduce((n, s) => n + s.size, 0);

  return (
    <motion.div className="p-6 space-y-4" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Management</h1>
          <p className="text-sm text-text-secondary mt-0.5">
            Analytical workspace — explore, compare and drill into workforce data
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <DateRangePicker value={dateRange} onChange={setDateRange} />
          <button
            onClick={() => setCompare((v) => !v)}
            className={`px-3 py-1.5 text-xs border rounded-btn transition-colors ${
              compare ? "border-accent text-accent bg-accent/5" : "border-border text-text-secondary hover:bg-nav-hover"
            }`}
          >
            Compare previous period
          </button>
          <button
            onClick={() => refresh.mutate()}
            disabled={refresh.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-btn text-text-secondary hover:bg-nav-hover disabled:opacity-50"
            title="Rebuild the analytics fact table"
          >
            <RefreshCw size={12} className={refresh.isPending ? "animate-spin" : ""} />
            Refresh
          </button>
          <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-btn text-text-secondary hover:bg-nav-hover">
            <Download size={12} />
            Export
          </button>
        </div>
      </div>

      {/* Global filter bar */}
      <div className="card-container p-3 flex items-center gap-2 flex-wrap">
        {FILTER_DIMENSIONS.map((key) => (
          <FilterDropdown
            key={key}
            label={dims?.dimensions.find((d) => d.key === key)?.label || key}
            columnKey={key}
            options={dimensionOptions[key] || []}
            selected={filters[key] || new Set()}
            onChange={setFilter}
          />
        ))}
        {activeFilterCount > 0 && (
          <button
            onClick={() => setFilters({})}
            className="flex items-center gap-1 px-2 py-1 text-xs text-accent hover:bg-nav-hover rounded-btn"
          >
            <X size={12} /> Clear all ({activeFilterCount})
          </button>
        )}
      </div>

      {/* Segmented control */}
      <SegmentedControl value={tab} options={TABS} onChange={setTab} />

      {/* Tab content */}
      {tab === "overview" && (
        <OverviewTab
          filters={apiFilters}
          dateRange={dateRangeObj}
          compare={compare}
          onDrill={drill}
          onGoToTab={(t) => setTab(t as Tab)}
        />
      )}

      {tab === "employees" && (
        <EmployeesTab filters={apiFilters} onOpenEmployee={setSelectedEmployeeId} />
      )}

      {tab === "attendance" && (
        <AttendanceTab
          filters={apiFilters}
          dateRange={dateRangeObj}
          compare={compare}
          onDrill={drill}
          onOpenEmployee={setSelectedEmployeeId}
        />
      )}

      {tab !== "overview" && tab !== "employees" && tab !== "attendance" && (
        <div className="card-container p-8 text-center text-sm text-text-secondary">
          <p className="font-medium text-text-primary capitalize">{tab} analytics</p>
          <p className="mt-1 text-text-muted">
            Deep {tab} analysis (KPIs, trends, comparison, group-by and drill-down) is built in the next phase.
          </p>
        </div>
      )}

      {selectedEmployeeId && (
        <EmployeeDetailDrawer
          employeeId={selectedEmployeeId}
          onClose={() => setSelectedEmployeeId(null)}
        />
      )}
    </motion.div>
  );
}
