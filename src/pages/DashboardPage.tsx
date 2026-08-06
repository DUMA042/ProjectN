import { useState } from "react";
import { motion } from "framer-motion";
import { Users, Target, TrendingUp, BarChart3, Layers } from "lucide-react";
import KpiCard from "@/components/ui/KpiCard";
import DonutChartCard from "@/components/charts/DonutChartCard";
import DeptAttendanceChart from "@/components/charts/DeptAttendanceChart";
import EarliestCheckinsCard from "@/components/ui/EarliestCheckinsCard";
import DataTable from "@/components/ui/DataTable";
import { getDefaultDateRange } from "@/components/ui/DateRangePicker";
import type { DateRange } from "@/components/ui/DateRangePicker";
import {
  useDashboardSummary,
  useCardSwipeSummary,
  useWorkforceStatus,
  useDeptAttendance,
  useEarliestCheckins,
  useEmployeeSummary,
  useDepartments,
} from "@/hooks/useDashboard";

const STATUS_COLORS: Record<string, string> = {
  "Active (Available)": "#10B981",
  "On Leave": "#F59E0B",
  "On Training": "#6366F1",
};

export default function DashboardPage() {
  const { data: summary, isLoading: summaryLoading } = useDashboardSummary();
  const { data: swipeSummary, isLoading: swipeLoading } = useCardSwipeSummary(true);
  const { data: empSummary, isLoading: empLoading } = useEmployeeSummary();
  const { data: departments } = useDepartments();

  // Chart-specific filters & date ranges
  const [deptDateRange, setDeptDateRange] = useState<DateRange>(getDefaultDateRange());
  const [workforceDateRange, setWorkforceDateRange] = useState<DateRange>(getDefaultDateRange());
  const [workforceDepartment, setWorkforceDepartment] = useState("");
  const [checkinDateRange, setCheckinDateRange] = useState<DateRange>(getDefaultDateRange());
  const [checkinLimit, setCheckinLimit] = useState(15);

  const { data: workforce, isLoading: workforceLoading } = useWorkforceStatus(
    workforceDateRange.startDate,
    workforceDateRange.endDate,
    workforceDepartment
  );
  const { data: deptAtt, isLoading: deptLoading } = useDeptAttendance(
    deptDateRange.startDate,
    deptDateRange.endDate
  );
  const { data: checkins, isLoading: checkinsLoading } = useEarliestCheckins(
    checkinDateRange.startDate,
    checkinDateRange.endDate,
    checkinLimit
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
      header: "Leave",
      cell: (row: any) => <span className="font-medium text-warning">{row.leave_records_count ?? "—"}</span>,
    },
    {
      key: "training_records_count",
      header: "Training",
      cell: (row: any) => <span className="font-medium text-info">{row.training_records_count ?? "—"}</span>,
    },
  ];

  return (
    <motion.div
      className="p-6 space-y-5"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Hello, Admin 👋</h1>
        <p className="text-sm text-text-secondary mt-0.5">Here is your daily workforce overview.</p>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-5 gap-4">
        <KpiCard title="Total Employees" value={summary?.total_employees ?? 0} icon={Users} loading={summaryLoading} />
        <KpiCard title="Active Workforce" value={summary?.active_employees ?? 0} icon={Target} loading={summaryLoading} />
        <KpiCard title="On Leave Today" value={summary?.staff_on_leave ?? 0} trend={-3} icon={Layers} loading={summaryLoading} />
        <KpiCard title="In Training" value={summary?.staff_in_training ?? 0} icon={TrendingUp} loading={summaryLoading} />
        <KpiCard title="Swipes Today" value={swipeSummary?.total_swipes ?? 0} trend={12} icon={BarChart3} loading={swipeLoading} />
      </div>

      {/* Top Charts Section: Department Attendance Performance & Earliest Check-Ins (Side-by-Side) */}
      <div className="grid grid-cols-[62fr_38fr] gap-5 items-stretch">
        <DeptAttendanceChart
          title="Department Attendance Performance"
          data={deptAtt || []}
          dateRange={deptDateRange}
          onDateChange={setDeptDateRange}
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

      {/* Workforce Status Distribution with Department & Day Filters */}
      <div>
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

      {/* Bottom Table */}
      <DataTable columns={empTableColumns} data={empSummary || []} loading={empLoading} searchable />
    </motion.div>
  );
}
