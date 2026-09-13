import { useState, useMemo, useEffect } from "react";
import { motion } from "framer-motion";
import type { SortingState } from "@tanstack/react-table";
import { Users, Target, TrendingUp, BarChart3, Layers, MapPin } from "lucide-react";
import { api } from "@/lib/api";
import { exportToCSV } from "@/lib/csvExport";
import KpiCard from "@/components/ui/KpiCard";
import DonutChartCard from "@/components/charts/DonutChartCard";
import DeptAttendanceChart from "@/components/charts/DeptAttendanceChart";
import EarliestCheckinsCard from "@/components/ui/EarliestCheckinsCard";
import type { CheckinMode } from "@/components/ui/EarliestCheckinsCard";
import ArrivalTimeChart from "@/components/charts/ArrivalTimeChart";
import DataTable from "@/components/ui/DataTable";
import DateRangePicker, { getDefaultDateRange } from "@/components/ui/DateRangePicker";
import EmployeeDetailSheet from "@/components/ui/EmployeeDetailSheet";
import type { DateRange } from "@/components/ui/DateRangePicker";
import {
  useDashboardSummary,
  useCardSwipeSummary,
  useWorkforceStatus,
  useDeptAttendance,
  useEarliestCheckins,
  useEmployeeSummary,
  useDepartments,
  useLocations,
  useArrivalTime,
} from "@/hooks/useDashboard";

function getLastMonthRange(): DateRange {
  const now = new Date();
  const first = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const last = new Date(now.getFullYear(), now.getMonth(), 0);
  const toISO = (d: Date) => d.toISOString().split("T")[0];
  return { startDate: toISO(first), endDate: toISO(last), label: "Last Month" };
}



const STATUS_COLORS: Record<string, string> = {
  "Active (Available)": "#52C41A",
  "On Leave": "#FAAD14",
  "On Training": "#1677FF",
};

export default function DashboardPage() {
  const [selectedLocation, setSelectedLocation] = useState("HQ");

  const { data: summary, isLoading: summaryLoading } = useDashboardSummary();
  const { data: swipeSummary, isLoading: swipeLoading } = useCardSwipeSummary(true);
  const { data: locations } = useLocations();
  const { data: departments } = useDepartments(selectedLocation);

  // Chart-specific filters & date ranges
  const [deptDateRange, setDeptDateRange] = useState<DateRange>(getDefaultDateRange());
  const [workforceDateRange, setWorkforceDateRange] = useState<DateRange>(getDefaultDateRange());
  const [workforceDepartment, setWorkforceDepartment] = useState("");
  const [checkinDateRange, setCheckinDateRange] = useState<DateRange>(getDefaultDateRange());
  const [checkinLimit, setCheckinLimit] = useState(15);
  const [arrivalTimeDateRange, setArrivalTimeDateRange] = useState<DateRange>(getLastMonthRange());
  const [arrivalTimeDepartment, setArrivalTimeDepartment] = useState("");
  const [empSummaryDateRange, setEmpSummaryDateRange] = useState<DateRange>(getDefaultDateRange());
  const [checkinMode, setCheckinMode] = useState<CheckinMode>("avg_checkin");
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string | null>(null);

  // Employee Summary — server-side table state
  const [empPage, setEmpPage] = useState(1);
  const [empPageSize, setEmpPageSize] = useState(25);
  const [empSearchInput, setEmpSearchInput] = useState("");
  const [empSearch, setEmpSearch] = useState("");
  const [empSorting, setEmpSorting] = useState<SortingState>([{ id: "full_name", desc: false }]);
  const [empColumnFilters, setEmpColumnFilters] = useState<Record<string, Set<string>>>({});

  // Debounce the search input so we don't hit the server on every keystroke
  useEffect(() => {
    const id = window.setTimeout(() => setEmpSearch(empSearchInput), 350);
    return () => window.clearTimeout(id);
  }, [empSearchInput]);

  const empSortBy = empSorting[0]?.id ?? "full_name";
  const empSortDir: "asc" | "desc" = empSorting[0]?.desc ? "desc" : "asc";
  const empFilters = useMemo(() => {
    const out: Record<string, string[]> = {};
    for (const [k, set] of Object.entries(empColumnFilters)) {
      if (set.size > 0) out[k] = [...set];
    }
    return out;
  }, [empColumnFilters]);

  // Reset to page 1 whenever the query inputs (location/date/search/sort/filters/size) change
  useEffect(() => {
    setEmpPage(1);
  }, [
    selectedLocation,
    empSummaryDateRange.startDate,
    empSummaryDateRange.endDate,
    empSearch,
    empSortBy,
    empSortDir,
    empFilters,
    empPageSize,
  ]);

  // Reset department filters if top-level location changes
  const handleLocationChange = (newLoc: string) => {
    setSelectedLocation(newLoc);
    setWorkforceDepartment("");
    setArrivalTimeDepartment("");
    setEmpSearchInput("");
    setEmpSearch("");
    setEmpColumnFilters({});
  };

  const { data: workforce, isLoading: workforceLoading } = useWorkforceStatus(
    workforceDateRange.startDate,
    workforceDateRange.endDate,
    workforceDepartment,
    selectedLocation
  );
  const { data: deptAtt, isLoading: deptLoading } = useDeptAttendance(
    deptDateRange.startDate,
    deptDateRange.endDate,
    "",
    selectedLocation
  );
  const { data: checkins, isLoading: checkinsLoading, isFetching: checkinsFetching } = useEarliestCheckins(
    checkinDateRange.startDate,
    checkinDateRange.endDate,
    checkinLimit,
    selectedLocation,
    checkinMode
  );
  const { data: arrivalTime, isLoading: arrivalTimeLoading } = useArrivalTime(
    arrivalTimeDateRange.startDate,
    arrivalTimeDateRange.endDate,
    arrivalTimeDepartment,
    selectedLocation
  );
  const { data: empSummaryData, isLoading: empLoading, isFetching: empFetching } = useEmployeeSummary({
    startDate: empSummaryDateRange.startDate,
    endDate: empSummaryDateRange.endDate,
    location: selectedLocation,
    page: empPage,
    pageSize: empPageSize,
    search: empSearch,
    sortBy: empSortBy,
    sortDir: empSortDir,
    filters: empFilters,
  });
  const empSummary = empSummaryData?.items ?? [];
  const empTotal = empSummaryData?.total ?? 0;
  const empFilterOptions = empSummaryData?.filter_options ?? {};

  // CSV export: fetch the full filtered set (same search/filters/sort, no pagination)
  const handleEmpExport = async () => {
    try {
      const res = await api.get("/api/dashboard/employee-summary", {
        params: {
          start_date: empSummaryDateRange.startDate,
          end_date: empSummaryDateRange.endDate,
          location: selectedLocation,
          page: 1,
          page_size: 0,
          search: empSearch,
          sort_by: empSortBy,
          sort_dir: empSortDir,
          filters: JSON.stringify(empFilters),
        },
      });
      exportToCSV(res.data?.items || [], "employee_summary_report", empSummaryDateRange);
    } catch {
      /* ignore export errors */
    }
  };

  const workforceDonut = (workforce || []).map((w: any) => ({
    name: w.status,
    value: w.count,
    color: STATUS_COLORS[w.status] || "#94A3B8",
    percentage: w.percentage,
  }));

  const empTableColumns = [
    { key: "full_name", header: "Full Name", sticky: true, width: 220 },
    { key: "id_no", header: "ID No", sticky: true, width: 110 },
    { key: "department", header: "Department" },
    { key: "grade_level", header: "Grade Level" },
    {
      key: "days_present",
      header: "Days Present",
      cell: (row: any) => <span className="font-medium text-success">{row.days_present ?? "—"}</span>,
    },
    {
      key: "absent_days",
      header: "Absent",
      cell: (row: any) => <span className="font-medium text-danger">{row.absent_days ?? "—"}</span>,
    },
    {
      key: "attendance_rate",
      header: "Attendance Rate",
      cell: (row: any) => {
        const rate = row.attendance_rate ?? 0;
        const color = rate >= 90 ? "text-success" : rate >= 70 ? "text-warning" : "text-danger";
        return <span className={`font-medium ${color}`}>{rate}%</span>;
      },
    },
    {
      key: "avg_checkin",
      header: "Avg Check-in",
      cell: (row: any) => <span className="font-mono text-text-secondary">{row.avg_checkin ?? "—"}</span>,
    },
    {
      key: "avg_checkout",
      header: "Avg Check-out",
      cell: (row: any) => <span className="font-mono text-text-secondary">{row.avg_checkout ?? "—"}</span>,
    },
    {
      key: "leave_days",
      header: "Leave Days",
      cell: (row: any) => <span className="font-medium text-warning">{row.leave_days ?? "—"}</span>,
    },
    {
      key: "training_days",
      header: "Training Days",
      cell: (row: any) => <span className="font-medium text-info">{row.training_days ?? "—"}</span>,
    },
  ];

  // Build location dropdown: All Location first, then HQ, then all other DB locations sorted
  const allLocations = locations || [];
  const otherLocations = allLocations.filter((l) => l !== "HQ").sort();
  const locationOptions = ["All Location", "HQ", ...otherLocations];

  return (
    <motion.div
      className="p-6 space-y-5"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      {/* Top Header with Location Filter on Top-Right */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Hello, Admin 👋</h1>
          <p className="text-sm text-text-secondary mt-0.5">Here is your daily workforce overview.</p>
        </div>

        <div className="flex items-center gap-2 bg-surface px-3 py-1.5 border border-border rounded-btn shadow-sm">
          <MapPin className="w-4 h-4 text-accent" />
          <span className="text-xs font-medium text-text-secondary">Location:</span>
          <select
            value={selectedLocation}
            onChange={(e) => handleLocationChange(e.target.value)}
            className="text-xs font-semibold bg-transparent text-text-primary focus:outline-none cursor-pointer pr-1"
          >
            {locationOptions.map((loc) => (
              <option key={loc} value={loc} className="bg-surface text-text-primary">
                {loc}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-5 gap-4">
        <KpiCard title="Total Employees" value={summary?.total_employees ?? 0} icon={Users} loading={summaryLoading} />
        <KpiCard title="Active Workforce" value={summary?.active_employees ?? 0} icon={Target} loading={summaryLoading} />
        <KpiCard title="On Leave Today" value={summary?.staff_on_leave ?? 0} icon={Layers} loading={summaryLoading} />
        <KpiCard title="In Training" value={summary?.staff_in_training ?? 0} icon={TrendingUp} loading={summaryLoading} />
        <KpiCard title="Swipes Today" value={swipeSummary?.total_swipes ?? 0} icon={BarChart3} loading={swipeLoading} />
      </div>

      {/* 2x2 Grid Section */}
      {/* Row 1: Department Attendance Performance (Left) & Earliest Check-Ins (Right) */}
      <div className="grid grid-cols-[62fr_38fr] gap-5 items-stretch">
        <DeptAttendanceChart
          title="Department Attendance Performance"
          data={deptAtt || []}
          dateRange={deptDateRange}
          onDateChange={setDeptDateRange}
          location={selectedLocation}
          loading={deptLoading}
        />

        <EarliestCheckinsCard
          title="Earliest Check-Ins"
          data={checkins || []}
          dateRange={checkinDateRange}
          onDateChange={setCheckinDateRange}
          limit={checkinLimit}
          onLimitChange={setCheckinLimit}
          loading={checkinsLoading}
          isFetching={checkinsFetching}
          mode={checkinMode}
          onModeChange={setCheckinMode}
        />
      </div>

      {/* Row 2: Arrival Time (Left, directly below Department Attendance Performance) & Workforce Status Distribution (Right, directly below Earliest Check-Ins) */}
      <div className="grid grid-cols-[62fr_38fr] gap-5 items-stretch">
        <ArrivalTimeChart
          title="Arrival Time"
          data={arrivalTime || []}
          dateRange={arrivalTimeDateRange}
          onDateChange={setArrivalTimeDateRange}
          selectedDepartment={arrivalTimeDepartment}
          onDepartmentChange={setArrivalTimeDepartment}
          departments={departments || []}
          loading={arrivalTimeLoading}
        />

        <DonutChartCard
          title="Workforce Status Distribution"
          data={workforceDonut}
          centerLabel={String(workforceDonut.reduce((s: number, d: any) => s + d.value, 0))}
          dateRange={workforceDateRange}
          onDateChange={setWorkforceDateRange}
          selectedDepartment={workforceDepartment}
          onDepartmentChange={setWorkforceDepartment}
          departments={departments || []}
          loading={workforceLoading}
        />
      </div>

      {/* Employee Summary Report with Date Filter */}
      <div className="space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h2 className="text-base font-semibold text-text-primary">Employee Summary Report</h2>
            <p className="text-xs text-text-secondary">Summary of presence, leave, and training records</p>
          </div>
          <DateRangePicker value={empSummaryDateRange} onChange={setEmpSummaryDateRange} />
        </div>
        <DataTable
          title="Employee Summary Report"
          columns={empTableColumns}
          data={empSummary}
          loading={empLoading}
          isFetching={empFetching}
          searchable
          enableColumnFilters
          serverSide
          total={empTotal}
          page={empPage}
          pageSize={empPageSize}
          onPageChange={setEmpPage}
          onPageSizeChange={(n) => { setEmpPageSize(n); setEmpPage(1); }}
          sorting={empSorting}
          onSortingChange={setEmpSorting}
          search={empSearchInput}
          onSearchChange={setEmpSearchInput}
          columnFilters={empColumnFilters}
          onColumnFiltersChange={setEmpColumnFilters}
          filterOptions={empFilterOptions}
          onRowClick={(row: any) => setSelectedEmployeeId(row.id_no)}
          dateRange={empSummaryDateRange}
          csvExportName="employee_summary_report"
          onExport={handleEmpExport}
        />
      </div>

      {/* Employee Detail Sheet */}
      {selectedEmployeeId && (
        <EmployeeDetailSheet
          employeeId={selectedEmployeeId}
          onClose={() => setSelectedEmployeeId(null)}
          defaultDateRange={empSummaryDateRange}
        />
      )}
    </motion.div>
  );
}

