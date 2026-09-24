import { useState, useEffect } from "react";
import type { SortingState } from "@tanstack/react-table";
import DataTable from "@/components/ui/DataTable";
import { useAnalyticsExplore } from "@/hooks/useAnalytics";
import { exportToCSV } from "@/lib/csvExport";
import { api } from "@/lib/api";

interface EmployeesTabProps {
  filters: Record<string, string[]>;
  onOpenEmployee: (id: string) => void;
}

export default function EmployeesTab({ filters, onOpenEmployee }: EmployeesTabProps) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [sorting, setSorting] = useState<SortingState>([{ id: "full_name", desc: false }]);

  useEffect(() => {
    const t = window.setTimeout(() => { setSearch(searchInput); setPage(1); }, 350);
    return () => window.clearTimeout(t);
  }, [searchInput]);

  const filtersKey = JSON.stringify(filters);
  useEffect(() => { setPage(1); }, [filtersKey]);

  const sortBy = sorting[0]?.id ?? "full_name";
  const sortDir: "asc" | "desc" = sorting[0]?.desc ? "desc" : "asc";

  const { data, isLoading, isFetching } = useAnalyticsExplore({
    domain: "employees",
    mode: "records",
    filters,
    page,
    page_size: pageSize,
    search,
    sort_by: sortBy,
    sort_dir: sortDir,
  });

  const columns = [
    { key: "id_no", header: "ID No" },
    { key: "full_name", header: "Full Name" },
    { key: "sex", header: "Sex" },
    { key: "department", header: "Department" },
    { key: "grade_level", header: "Grade Level" },
    {
      key: "status",
      header: "Status",
      cell: (r: any) => (
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
          (r.status || "").toLowerCase() === "active"
            ? "bg-badge-green-bg text-badge-green-text"
            : "bg-nav-hover text-text-secondary"
        }`}>
          {r.status}
        </span>
      ),
    },
  ];

  const handleExport = async () => {
    try {
      const res = await api.post("/api/analytics/explore", {
        domain: "employees", mode: "records", filters, page: 1, page_size: 0,
        search, sort_by: sortBy, sort_dir: sortDir,
      });
      exportToCSV(res.data?.records || [], "employees");
    } catch {
      /* ignore export errors */
    }
  };

  return (
    <DataTable
      title="Employees"
      columns={columns}
      data={data?.records || []}
      loading={isLoading}
      isFetching={isFetching}
      searchable
      serverSide
      total={data?.total ?? 0}
      page={page}
      pageSize={pageSize}
      pageSizeOptions={[25, 50, 100]}
      onPageChange={setPage}
      onPageSizeChange={(n) => { setPageSize(n); setPage(1); }}
      sorting={sorting}
      onSortingChange={setSorting}
      search={searchInput}
      onSearchChange={setSearchInput}
      onRowClick={(r: any) => onOpenEmployee(r.id_no)}
      csvExportName="employees"
      onExport={handleExport}
    />
  );
}
