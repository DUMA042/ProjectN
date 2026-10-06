import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface EmployeeOption {
  id_no: string;
  full_name: string;
  department: string;
  rank: string;
  grade_level: string;
}

export interface IndividualBuildResult {
  job_id: string;
  stage: string;
  headcount: number;
  filename: string;
  download_url: string;
}

export interface IndividualStoredReport {
  job_id: string;
  filename: string;
  created_at: string;
  location: string;
  departments: string[];
  headcount: number;
  period: string;
  download_url: string;
}

export function useLocations() {
  return useQuery<string[]>({
    queryKey: ["lookup-locations"],
    queryFn: () => api.get("/api/dashboard/locations").then((r) => r.data),
    staleTime: 60_000,
  });
}

export function useDepartments(location: string) {
  return useQuery<string[]>({
    queryKey: ["lookup-departments", location],
    queryFn: () =>
      api
        .get("/api/dashboard/departments", { params: location ? { location } : {} })
        .then((r) => r.data),
    staleTime: 60_000,
  });
}

export interface StaffSearchResult {
  items: EmployeeOption[];
  total: number;
}

/** Paginated staff search for the individuals picker. */
export async function searchStaff(
  search: string,
  department: string,
  location: string,
  page = 1,
  size = 50
): Promise<StaffSearchResult> {
  const res = await api.get("/api/staff", {
    params: { search, department, location, page, size },
  });
  return { items: res.data.items as EmployeeOption[], total: res.data.total as number };
}

/** Start a deterministic individual-report build: returns immediately,
 *  progress streams into the job (poll via useBuildJob). */
export async function buildIndividualReport(body: {
  location: string;
  departments: string[];
  employee_ids: string[];
  search: string;
  start_date: string;
  end_date: string;
}): Promise<{ job_id: string; stage: string }> {
  const res = await api.post("/api/individual-reports/build", body, { timeout: 30_000 });
  return res.data as { job_id: string; stage: string };
}

/** Cancel a running individual build. */
export async function cancelIndividualBuild(jobId: string): Promise<void> {
  await api.post(`/api/individual-reports/${jobId}/cancel`);
}

/** Finished individual reports (filesystem-backed library). */
export function useIndividualReports() {
  return useQuery<{ reports: IndividualStoredReport[] }>({
    queryKey: ["individual-reports"],
    queryFn: () => api.get("/api/individual-reports").then((r) => r.data),
    staleTime: 30_000,
  });
}
