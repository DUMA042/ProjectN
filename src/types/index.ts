export interface KpiMetric {
  title: string;
  value: number;
  trend: number;
  sparklineData: number[];
}

export interface Employee {
  id_no: string;
  full_name: string;
  sex: string;
  department: string;
  rank: string;
  grade_level: string;
  status: string;
  geographical_zone: string;
  date_of_last_deployment: string | null;
}

export interface SwipeRecord {
  swipe_id: number;
  id_no: string;
  full_name: string;
  swipe_time: string;
  location: string;
}

export interface LeaveRecord {
  record_id: number;
  id_no: string;
  full_name: string;
  leave_type_name: string;
  start_date: string;
  end_date: string;
}

export interface TrainingRecord {
  training_id: number;
  id_no: string;
  full_name: string;
  venue: string;
  consultant: string;
  start_date: string;
  end_date: string;
  title: string | null;
}

export interface DepartmentDistribution {
  department_name: string;
  employee_count: number;
}

export interface StatusDistribution {
  status_name: string;
  employee_count: number;
}

export interface WorkforceStatus {
  status: "Present" | "Absent" | "On Leave" | "In Training";
  count: number;
}

export interface LeaderboardEntry {
  rank: number;
  id_no: string;
  full_name: string;
  department: string;
  swipe_time: string;
}

export interface EmployeeSummary {
  id_no: string;
  full_name: string;
  department: string;
  grade_level: string;
  days_present: number;
  days_absent: number;
  days_leave: number;
}

export interface IngestionRecord {
  id: string;
  original_filename: string;
  normalized_filename: string;
  report_type: string;
  status: string;
  created_at: string;
}

export interface NavSection {
  label: string;
  items: NavItem[];
}

export interface NavItem {
  icon: string;
  label: string;
  path: string;
  children?: NavItem[];
}
