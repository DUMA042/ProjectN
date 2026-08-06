import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { getDefaultDateRange } from "@/components/ui/DateRangePicker";

const today = getDefaultDateRange();

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
  department: string = ""
) {
  return useQuery({
    queryKey: ["workforce-status", startDate, endDate, department],
    queryFn: () =>
      api
        .get("/api/dashboard/workforce-status", {
          params: { start_date: startDate, end_date: endDate, department },
        })
        .then((r) => r.data),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}

export function useDeptAttendance(
  startDate: string = today.startDate,
  endDate: string = today.endDate,
  department: string = ""
) {
  return useQuery({
    queryKey: ["dept-attendance", startDate, endDate, department],
    queryFn: () =>
      api
        .get("/api/dashboard/dept-attendance", {
          params: { start_date: startDate, end_date: endDate, department },
        })
        .then((r) => r.data),
    refetchInterval: 120_000,
    staleTime: 60_000,
  });
}

export function useEarliestCheckins(
  startDate: string = today.startDate,
  endDate: string = today.endDate,
  limit: number = 10
) {
  return useQuery({
    queryKey: ["earliest-checkins", startDate, endDate, limit],
    queryFn: () =>
      api
        .get("/api/dashboard/earliest-checkins", {
          params: { start_date: startDate, end_date: endDate, limit },
        })
        .then((r) => r.data),
    refetchInterval: 30_000,
    staleTime: 15_000,
  });
}

export function useEmployeeSummary() {
  return useQuery({
    queryKey: ["employee-summary"],
    queryFn: () =>
      api.get("/api/dashboard/employee-summary").then((r) => r.data),
    refetchInterval: 120_000,
    staleTime: 60_000,
  });
}
