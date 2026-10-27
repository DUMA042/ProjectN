/** Shared shapes for the employee directory and roster editor. */

export interface LookupOption {
  id: number;
  name: string;
}

export interface EmployeeLookups {
  departments: LookupOption[];
  ranks: LookupOption[];
  grade_levels: LookupOption[];
  employment_types: LookupOption[];
  statuses: LookupOption[];
  zones: string[];
  sexes: string[];
}

export interface EmployeeDetail {
  id_no: string;
  full_name: string;
  sex: string | null;
  department: string | null;
  department_id: number | null;
  rank: string | null;
  rank_id: number | null;
  grade_level: string | null;
  gl_id: number | null;
  status: string | null;
  status_id: number | null;
  employment_type: string | null;
  emp_type_id: number | null;
  geographical_zone: string | null;
  date_of_last_deployment: string | null;
  phone_number: string | null;
  remark: string | null;
  card_swipes: { swipe_id: number; swipe_time: string; location: string }[];
  leave_records: { record_id: number; leave_type_name: string; start_date: string; end_date: string }[];
  training_records: { training_id: number; venue: string; consultant: string; start_date: string; end_date: string; title: string | null }[];
}

/** Fields the roster editor may change. `id_no` is intentionally absent. */
export interface EmployeeUpdatePayload {
  full_name?: string;
  sex?: string | null;
  phone_number?: string | null;
  geographical_zone?: string | null;
  date_of_last_deployment?: string | null;
  department_id?: number | null;
  rank_id?: number | null;
  gl_id?: number | null;
  emp_type_id?: number | null;
  status_id?: number | null;
}
