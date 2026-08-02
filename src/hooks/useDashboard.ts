import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () => api.get("/api/analytics/summary").then((r) => r.data),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}

export function useCardSwipeSummary(today = true) {
  return useQuery({
    queryKey: ["card-swipe-summary", today],
    queryFn: () =>
      api.get(`/api/card-swipe/summary?today=${today}`).then((r) => r.data),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}

export function useDepartmentDistribution() {
  return useQuery({
    queryKey: ["department-distribution"],
    queryFn: () => api.get("/api/analytics/departments").then((r) => r.data),
    refetchInterval: 300_000,
    staleTime: 120_000,
  });
}

export function useWorkforceStatus() {
  return useQuery({
    queryKey: ["workforce-status"],
    queryFn: () =>
      api.get("/api/dashboard/workforce-status").then((r) => r.data),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}

export function useEarliestCheckins(limit = 10) {
  return useQuery({
    queryKey: ["earliest-checkins", limit],
    queryFn: () =>
      api
        .get(`/api/dashboard/earliest-checkins?limit=${limit}`)
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
