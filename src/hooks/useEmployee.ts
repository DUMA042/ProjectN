import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { EmployeeDetail, EmployeeLookups, EmployeeUpdatePayload } from "@/lib/staff";

export function useEmployeeLookups(enabled = true) {
  return useQuery({
    queryKey: ["employee-lookups"],
    queryFn: () =>
      api.get("/api/employees/lookups").then((r) => r.data as EmployeeLookups),
    staleTime: 300_000,
    enabled,
  });
}

export function useEmployeeUpdate(idNo: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (changes: EmployeeUpdatePayload) =>
      api
        .patch(`/api/employees/${idNo}`, changes)
        .then((r) => r.data as EmployeeDetail),
    onSuccess: (data) => {
      // Keep the swipe/leave/training sections already loaded in the drawer.
      qc.setQueryData<EmployeeDetail>(["employee-detail", idNo], (old) =>
        old ? { ...old, ...data } : data
      );
      qc.invalidateQueries({ queryKey: ["employee-detail", idNo] });
      qc.invalidateQueries({ queryKey: ["employee-attendance-90d", idNo] });
      qc.invalidateQueries({ queryKey: ["employee-dept-rate"] });
      qc.invalidateQueries({ queryKey: ["analytics-explore"] });
    },
  });
}
