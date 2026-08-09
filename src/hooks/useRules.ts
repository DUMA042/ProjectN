import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useRules() {
  return useQuery({
    queryKey: ["rules"],
    queryFn: () => api.get("/api/rules").then((r) => r.data),
    staleTime: 60_000,
  });
}

export function useUpdateRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: any }) =>
      api.put(`/api/rules/${key}`, { value }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });
}

export function useSeedRules() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post("/api/rules/seed"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });
}
