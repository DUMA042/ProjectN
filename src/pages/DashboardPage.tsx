import { useState } from "react";
import { motion } from "framer-motion";
import { Users, Target, TrendingUp, BarChart3, Layers, MapPin } from "lucide-react";
import KpiCard from "@/components/ui/KpiCard";
import DonutChartCard from "@/components/charts/DonutChartCard";
import DeptAttendanceChart from "@/components/charts/DeptAttendanceChart";
import EarliestCheckinsCard from "@/components/ui/EarliestCheckinsCard";
import ArrivalTimeChart from "@/components/charts/ArrivalTimeChart";
import DataTable from "@/components/ui/DataTable";
import DateRangePicker, { getDefaultDateRange } from "@/components/ui/DateRangePicker";
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
  "Active (Available)": "#10B981",
  "On Leave": "#F59E0B",
  "On Training": "#6366F1",
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

  // Reset department filters if top-level location changes
  const handleLocationChange = (newLoc: string) => {
    setSelectedLocation(newLoc);
    setWorkforceDepartment("");
    setArrivalTimeDepartment("");
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
  const { data: checkins, isLoading: checkinsLoading } = useEarliestCheckins(
    checkinDateRange.startDate,
    checkinDateRange.endDate,
    checkinLimit,
    selectedLocation
  );
  const { data: arrivalTime, isLoading: arrivalTimeLoading } = useArrivalTime(
    arrivalTimeDateRange.startDate,
    arrivalTimeDateRange.endDate,
    arrivalTimeDepartment,
    selectedLocation
  );
  const { data: empSummary, isLoading: empLoading } = useEmployeeSummary(
    empSummaryDateRange.startDate,
    empSummaryDateRange.endDate,
    selectedLocation
  );

  const workforceDonut = (workforce || []).map((w: any) => ({
    name: w.status,
    value: w.count,
    color: STATUS_COLORS[w.status] || "#94A3B8",
    percentage: w.percentage,
  }));

  const empTableColumns = [
    { key: "full_name", header: "Full Name" },
    { key: "id_no", header: "ID No" },
    { key: "department", header: "Department" },
    { key: "grade_level", header: "Grade Level" },
    {
      key: "days_present",
      header: "Days Present",
      cell: (row: any) => <span className="font-medium text-success">{row.days_present ?? "—"}</span>,
    },
    {
      key: "leave_records_count",
      header: "Leave Records",
      cell: (row: any) => <span className="font-medium text-warning">{row.leave_records_count ?? "—"}</span>,
    },
    {
      key: "training_records_count",
      header: "Training Records",
      cell: (row: any) => <span className="font-medium text-info">{row.training_records_count ?? "—"}</span>,
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
        <DataTable title="Employee Summary Report" columns={empTableColumns} data={empSummary || []} loading={empLoading} searchable />
      </div>
    </motion.div>
  );
}

