import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Download } from "lucide-react";
import DateRangePicker from "@/components/ui/DateRangePicker";
import ErrorBoundary from "@/components/ui/ErrorBoundary";
import SegmentedControl from "@/components/analytics/SegmentedControl";
import LocationSelect from "@/components/analytics/LocationSelect";
import FreshnessPill from "@/components/analytics/FreshnessPill";
import ScopeChips from "@/components/analytics/ScopeChips";
import FilterPopover from "@/components/analytics/FilterPopover";
import SavedViewsMenu from "@/components/analytics/SavedViewsMenu";
import EmployeeDetailDrawer from "@/components/ui/EmployeeDetailDrawer";
import PulseTab from "./management/PulseTab";
import TrendsTab from "./management/TrendsTab";
import ExploreTab from "./management/ExploreTab";
import PeopleTab from "./management/PeopleTab";
import ForecastTab from "./management/ForecastTab";
import NarrativeHeader from "./management/kpiConfig";
import { ExportProvider, useExportButton } from "./management/exportRegistry";
import { useManagementScope, scopeToApiFilters, type ManagementTab } from "@/hooks/useManagementScope";

const TABS: { value: ManagementTab; label: string }[] = [
  { value: "pulse", label: "Pulse" },
  { value: "trends", label: "Trends" },
  { value: "explore", label: "Explore" },
  { value: "people", label: "People" },
  { value: "forecast", label: "Forecast" },
];

function ExportButton() {
  const { exportNow, hasExport } = useExportButton();
  return (
    <button
      onClick={exportNow}
      disabled={!hasExport}
      className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs border border-border rounded-btn transition-colors ${
        hasExport ? "text-text-secondary hover:bg-nav-hover" : "text-text-muted opacity-50 cursor-not-allowed"
      }`}
      title={hasExport ? "Export the tables on this tab to CSV" : "This tab has no exportable table"}
    >
      <Download size={12} />
      Export
    </button>
  );
}

export default function ManagementPage() {
  const {
    tab, location, dateRange, compare, filters, peopleEntity,
    setTab, setLocation, setDateRange, setCompare, setPeopleEntity, addFilter,
  } = useManagementScope();
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string | null>(null);

  const apiFilters = useMemo(() => scopeToApiFilters(filters, location), [filters, location]);
  const dateRangeObj = useMemo(
    () => ({ start: dateRange.startDate, end: dateRange.endDate }),
    [dateRange.startDate, dateRange.endDate]
  );

  /** Drill helper — location values scope the location selector, others become chips. */
  const drill = (dimension: string, value: string) => {
    if (dimension === "location") setLocation(value);
    else addFilter(dimension, value);
  };

  return (
    <ExportProvider>
      <motion.div
        className="p-6 space-y-4"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
      >
        {/* ── Header ─────────────────────────────────────────────────────── */}
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-lg font-semibold text-text-primary">Management</h1>
            <p className="text-xs text-text-secondary mt-0.5">
              The organization at a glance — what is happening, when, to whom, and what comes next
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <LocationSelect value={location} onChange={setLocation} />
            <FreshnessPill filters={apiFilters} />
            <ExportButton />
          </div>
        </div>

        {/* ── Scope bar ──────────────────────────────────────────────────── */}
        <div className="card-container p-3 flex items-center gap-2 flex-wrap">
          <DateRangePicker value={dateRange} onChange={setDateRange} />
          <button
            onClick={() => setCompare(!compare)}
            className={`px-3 py-1.5 text-xs border rounded-btn transition-colors ${
              compare
                ? "border-accent text-accent bg-accent/5"
                : "border-border text-text-secondary hover:bg-nav-hover"
            }`}
            title="Overlays the previous period of equal length on trends, deltas and KPI chips — e.g. Last 90 Days compares against the 90 days before it"
          >
            Compare previous
          </button>
          <FilterPopover />
          <ScopeChips />
          <div className="ml-auto">
            <SavedViewsMenu />
          </div>
        </div>

        {/* ── Tabs ───────────────────────────────────────────────────────── */}
        <SegmentedControl value={tab} options={TABS} onChange={setTab} />

        <NarrativeHeader filters={apiFilters} dateRange={dateRangeObj} compare={compare} />

        {/* ── Tab content ────────────────────────────────────────────────── */}
        <ErrorBoundary label="this view">
          <AnimatePresence mode="wait">
            <motion.div
              key={tab}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.18, ease: "easeOut" }}
            >
              {tab === "pulse" && (
                <PulseTab
                  filters={apiFilters}
                  dateRange={dateRangeObj}
                  compare={compare}
                  onDrill={drill}
                  onGoToTab={(t) => setTab(t as ManagementTab)}
                  onOpenEmployee={setSelectedEmployeeId}
                />
              )}
              {tab === "trends" && (
                <TrendsTab filters={apiFilters} dateRange={dateRangeObj} compare={compare} onDrill={drill} />
              )}
              {tab === "explore" && (
                <ExploreTab filters={apiFilters} dateRange={dateRangeObj} onDrill={drill} onOpenEmployee={setSelectedEmployeeId} />
              )}
              {tab === "people" && (
                <PeopleTab
                  filters={apiFilters}
                  dateRange={dateRangeObj}
                  compare={compare}
                  onDrill={drill}
                  onOpenEmployee={setSelectedEmployeeId}
                />
              )}
              {tab === "forecast" && (
                <ForecastTab filters={apiFilters} onOpenEmployee={setSelectedEmployeeId} />
              )}
            </motion.div>
          </AnimatePresence>
        </ErrorBoundary>

        {selectedEmployeeId && (
          <EmployeeDetailDrawer employeeId={selectedEmployeeId} onClose={() => setSelectedEmployeeId(null)} />
        )}
      </motion.div>
    </ExportProvider>
  );
}
