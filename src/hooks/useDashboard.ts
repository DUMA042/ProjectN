import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { getDefaultDateRange } from "@/components/ui/DateRangePicker";

const today = getDefaultDateRange();

export function useLocations() {
  return useQuery({
    queryKey: ["locations-list"],
    queryFn: () =>
      api.get("/api/dashboard/locations").then((r) => (r.data as string[]) || []),
    staleTime: 300_000,
  });
}

export function useDepartments(location: string = "") {
  return useQuery({
    queryKey: ["departments-list", location],
    queryFn: () =>
      api
        .get("/api/dashboard/departments", { params: { location } })
        .then((r) => (r.data as string[]) || []),
    staleTime: 300_000,
  });
}

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () => api.get("/api/analytics/summary").then((r) => r.data),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}

export function useCardSwipeSummary(todayOnly = true) {
  return useQuery({
    queryKey: ["card-swipe-summary", todayOnly],
    queryFn: () =>
      api.get(`/api/card-swipe/summary?today=${todayOnly}`).then((r) => r.data),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}

export function useWorkforceStatus(
  startDate: string = today.startDate,
  endDate: string = today.endDate,
  department: string = "",
  location: string = ""
) {
  return useQuery({
    queryKey: ["workforce-status", startDate, endDate, department, location],
    queryFn: () =>
      api
        .get("/api/dashboard/workforce-status", {
          params: { start_date: startDate, end_date: endDate, department, location },
        })
        .then((r) => r.data),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}

export function useDeptAttendance(
  startDate: string = today.startDate,
  endDate: string = today.endDate,
  department: string = "",
  location: string = ""
) {
  return useQuery({
    queryKey: ["dept-attendance", startDate, endDate, department, location],
    queryFn: () =>
      api
        .get("/api/dashboard/dept-attendance", {
          params: { start_date: startDate, end_date: endDate, department, location },
        })
        .then((r) => r.data),
    refetchInterval: 120_000,
    staleTime: 60_000,
  });
}

export function useEarliestCheckins(
  startDate: string = today.startDate,
  endDate: string = today.endDate,
  limit: number = 10,
  location: string = ""
) {
  return useQuery({
    queryKey: ["earliest-checkins", startDate, endDate, limit, location],
    queryFn: () =>
      api
        .get("/api/dashboard/earliest-checkins", {
          params: { start_date: startDate, end_date: endDate, limit, location },
        })
        .then((r) => r.data),
    refetchInterval: 30_000,
    staleTime: 15_000,
  });
}

export function useArrivalTime(
  startDate: string = today.startDate,
  endDate: string = today.endDate,
  department: string = "",
  location: string = ""
) {
  return useQuery({
    queryKey: ["arrival-time", startDate, endDate, department, location],
    queryFn: () =>
      api
        .get("/api/dashboard/arrival-time", {
          params: { start_date: startDate, end_date: endDate, department, location },
        })
        .then((r) => r.data),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}

export function useEmployeeSummary(
  startDate: string = "",
  endDate: string = "",
  location: string = ""
) {
  return useQuery({
    queryKey: ["employee-summary", startDate, endDate, location],
    queryFn: () =>
      api
        .get("/api/dashboard/employee-summary", {
          params: { start_date: startDate, end_date: endDate, location },
        })
        .then((r) => r.data),
    refetchInterval: 120_000,
    staleTime: 60_000,
  });
}


