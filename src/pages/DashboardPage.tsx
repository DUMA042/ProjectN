import { motion } from "framer-motion";
import { Users, Target, TrendingUp, BarChart3, Layers } from "lucide-react";
import KpiCard from "@/components/ui/KpiCard";
import BarChartCard from "@/components/charts/BarChartCard";
import DonutChartCard from "@/components/charts/DonutChartCard";
import LeaderboardCard from "@/components/ui/LeaderboardCard";
import DataTable from "@/components/ui/DataTable";
import {
  useDashboardSummary,
  useCardSwipeSummary,
  useDepartmentDistribution,
  useWorkforceStatus,
  useEarliestCheckins,
  useEmployeeSummary,
} from "@/hooks/useDashboard";

const STATUS_COLORS: Record<string, string> = {
  Present: "#10B981",
  Absent: "#EF4444",
  "On Leave": "#F59E0B",
  "In Training": "#6366F1",
};

export default function DashboardPage() {
  const { data: summary, isLoading: summaryLoading } = useDashboardSummary();
  const { data: swipeSummary, isLoading: swipeLoading } = useCardSwipeSummary(true);
  const { data: departments, isLoading: deptLoading } = useDepartmentDistribution();
  const { data: workforce, isLoading: workforceLoading } = useWorkforceStatus();
  const { data: checkins, isLoading: checkinsLoading } = useEarliestCheckins(10);
  const { data: empSummary, isLoading: empLoading } = useEmployeeSummary();

  const deptChartData = (departments || []).slice(0, 20).map((d: any) => ({
    label: d.department_name,
    value: d.employee_count,
  }));

  const workforceDonut = (workforce || []).map((w: any) => ({
    name: w.status,
    value: w.count,
    color: STATUS_COLORS[w.status] || "#94A3B8",
  }));

  const empTableColumns = [
    { key: "full_name", header: "Full Name" },
    { key: "id_no", header: "ID No" },
    { key: "department", header: "Department" },
    { key: "grade_level", header: "Grade Level" },
    {
      key: "days_present",
      header: "Days Present",
      cell: (row: any) => (
        <span className="font-medium text-success">{row.days_present ?? "—"}</span>
      ),
    },
    {
      key: "leave_records_count",
      header: "Leave Count",
      cell: (row: any) => (
        <span className="font-medium text-warning">{row.leave_records_count ?? "—"}</span>
      ),
    },
    {
      key: "training_records_count",
      header: "Training",
      cell: (row: any) => (
        <span className="font-medium text-info">{row.training_records_count ?? "—"}</span>
      ),
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
        <h1 className="text-xl font-semibold text-text-primary">
          Hello, Admin 👋
        </h1>
        <p className="text-sm text-text-secondary mt-0.5">
          Here is your daily workforce overview.
        </p>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-5 gap-4">
        <KpiCard
          title="Total Employees"
          value={summary?.total_employees ?? 0}
          icon={Users}
          loading={summaryLoading}
          sparklineData={[1620, 1615, 1630, 1640, 1650, 1655, summary?.total_employees ?? 0]}
        />
        <KpiCard
          title="Active Workforce"
          value={summary?.active_employees ?? 0}
          icon={Target}
          loading={summaryLoading}
          sparklineData={[1600, 1590, 1605, 1610, 1615, 1613, summary?.active_employees ?? 0]}
        />
        <KpiCard
          title="On Leave Today"
          value={summary?.staff_on_leave ?? 0}
          trend={-3}
          icon={Layers}
          loading={summaryLoading}
        />
        <KpiCard
          title="In Training"
          value={summary?.staff_in_training ?? 0}
          icon={TrendingUp}
          loading={summaryLoading}
        />
        <KpiCard
          title="Swipes Today"
          value={swipeSummary?.total_swipes ?? 0}
          trend={12}
          icon={BarChart3}
          loading={swipeLoading}
        />
      </div>

      {/* Middle Grid */}
      <div className="grid grid-cols-[65fr_35fr] gap-5">
        {/* Left Column */}
        <div className="space-y-5">
          <BarChartCard
            title="Department Distribution"
            data={deptChartData}
            loading={deptLoading}
          />

          <DonutChartCard
            title="Workforce Status Distribution"
            data={workforceDonut}
            centerLabel={String(summary?.total_employees ?? "")}
            loading={workforceLoading}
          />
        </div>

        {/* Right Column */}
        <LeaderboardCard
          title="Top 10 Earliest Check-Ins 🏆"
          data={checkins || []}
          loading={checkinsLoading}
        />
      </div>

      {/* Bottom Table */}
      <DataTable
        columns={empTableColumns}
        data={empSummary || []}
        loading={empLoading}
        searchable
      />
    </motion.div>
  );
}
