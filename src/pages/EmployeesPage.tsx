import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, X, ChevronUp, ChevronDown, ChevronsUpDown,
  User, Clock, Umbrella, GraduationCap,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface Employee {
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

interface EmployeeDetail {
  id_no: string;
  full_name: string;
  sex: string;
  department: string;
  rank: string;
  grade_level: string;
  status: string;
  employment_type: string;
  geographical_zone: string;
  date_of_last_deployment: string | null;
  phone_number: string | null;
  remark: string | null;
  card_swipes: { swipe_id: number; swipe_time: string; location: string }[];
  leave_records: { record_id: number; leave_type_name: string; start_date: string; end_date: string }[];
  training_records: { training_id: number; venue: string; consultant: string; start_date: string; end_date: string; title: string | null }[];
}

interface StaffListResponse {
  page: number;
  size: number;
  total: number;
  items: Employee[];
}

function useStaffList(page: number, size: number, search: string, department: string, status: string) {
  return useQuery({
    queryKey: ["staff-list", page, size, search, department, status],
    queryFn: () =>
      api.get("/api/staff", { params: { page, size, search, department: department || undefined, status: status || undefined } })
        .then((r) => r.data as StaffListResponse),
    staleTime: 30_000,
  });
}

function useDepartments() {
  return useQuery({
    queryKey: ["departments-list"],
    queryFn: () => api.get("/api/dashboard/departments?location=HQ").then((r) => r.data as string[]),
    staleTime: 300_000,
  });
}

function useStatuses() {
  return useQuery({
    queryKey: ["statuses-list"],
    queryFn: () => api.get("/api/analytics/statuses").then((r) => r.data as { status_name: string }[]),
    staleTime: 300_000,
    select: (data) => (data || []).map((d: any) => d.status_name || d.name || "").filter(Boolean),
  });
}

function useEmployeeDetail(idNo: string | null) {
  return useQuery({
    queryKey: ["employee-detail", idNo],
    queryFn: () => api.get(`/api/employees/${idNo}/detail`).then((r) => r.data as EmployeeDetail),
    enabled: !!idNo,
  });
}

export default function EmployeesPage() {
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(25);
  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState("");
  const [status, setStatus] = useState("");
  const [sortBy, setSortBy] = useState<string>("full_name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, isLoading } = useStaffList(page, size, search, department, status);
  const { data: departments } = useDepartments();
  const { data: statuses } = useStatuses();
  const { data: detail, isLoading: detailLoading } = useEmployeeDetail(selectedId);

  const total = data?.total || 0;
  const items = data?.items || [];
  const totalPages = Math.max(1, Math.ceil(total / size));

  const handleSort = (col: string) => {
    if (sortBy === col) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortBy(col);
      setSortDir("asc");
    }
  };

  const sortIcon = (col: string) => {
    if (sortBy !== col) return <ChevronsUpDown size={14} className="opacity-40" />;
    return sortDir === "asc" ? <ChevronUp size={14} /> : <ChevronDown size={14} />;
  };

  const COLUMNS = [
    { key: "id_no", label: "ID No", width: "w-[90px]", align: "left" },
    { key: "full_name", label: "Full Name", width: "min-w-[180px]", align: "left" },
    { key: "sex", label: "Sex", width: "w-[60px]", align: "left" },
    { key: "department", label: "Department", width: "min-w-[140px]", align: "left" },
    { key: "rank", label: "Rank", width: "min-w-[120px]", align: "left" },
    { key: "grade_level", label: "GL", width: "w-[60px]", align: "left" },
    { key: "status", label: "Status", width: "w-[100px]", align: "left" },
    { key: "geographical_zone", label: "Zone", width: "w-[100px]", align: "left" },
  ];

  return (
    <motion.div className="p-6 space-y-4" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Employees</h1>
        <p className="text-sm text-text-secondary mt-0.5">
          Staff directory with search, filter, and detail views
        </p>
      </div>

      {/* Filter bar */}
      <div className="card-container p-3 flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-[320px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            placeholder="Search by name or ID..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="w-full pl-9 pr-3 py-2 text-sm border border-border rounded-input bg-surface text-text-primary placeholder-text-muted focus:outline-none focus:border-accent transition-colors"
          />
        </div>
        <select
          value={department}
          onChange={(e) => { setDepartment(e.target.value); setPage(1); }}
          className="px-3 py-2 text-sm border border-border rounded-input bg-surface text-text-secondary cursor-pointer hover:border-text-muted transition-colors"
        >
          <option value="">All Departments</option>
          {(departments || []).map((d: any) => (
            <option key={typeof d === "string" ? d : d.department_name} value={typeof d === "string" ? d : d.department_name}>
              {typeof d === "string" ? d : d.department_name}
            </option>
          ))}
        </select>
        <select
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(1); }}
          className="px-3 py-2 text-sm border border-border rounded-input bg-surface text-text-secondary cursor-pointer hover:border-text-muted transition-colors"
        >
          <option value="">All Statuses</option>
          {(statuses || []).map((s: string) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <span className="text-xs text-text-muted ml-auto">
          {total.toLocaleString()} employees
        </span>
      </div>

      {/* Table */}
      <div className="card-container overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-divider">
                {COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className={`${col.width} text-left px-4 py-2.5 text-table-header text-text-muted uppercase tracking-wider cursor-pointer select-none hover:text-text-secondary transition-colors`}
                  >
                    <div className="flex items-center gap-1.5">
                      {col.label}
                      {sortIcon(col.key)}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(10)].map((_, i) => (
                  <tr key={i} className="border-b border-divider">
                    {COLUMNS.map((col) => (
                      <td key={col.key} className="px-4 py-3"><div className="h-4 bg-nav-hover rounded animate-pulse" /></td>
                    ))}
                  </tr>
                ))
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={COLUMNS.length} className="px-4 py-12 text-center">
                    <User size={36} className="mx-auto text-text-muted mb-3" strokeWidth={1.5} />
                    <p className="text-sm text-text-secondary">No employees found</p>
                    <p className="text-xs text-text-muted mt-1">Try adjusting your search or filters</p>
                  </td>
                </tr>
              ) : (
                items.map((emp) => (
                  <tr
                    key={emp.id_no}
                    onClick={() => setSelectedId(emp.id_no)}
                    className="border-b border-divider last:border-0 hover:bg-nav-hover transition-colors cursor-pointer"
                  >
                    <td className="px-4 py-2.5 text-sm text-text-primary font-mono">{emp.id_no}</td>
                    <td className="px-4 py-2.5 text-sm text-text-primary font-medium">{emp.full_name}</td>
                    <td className="px-4 py-2.5 text-sm text-text-secondary">{emp.sex}</td>
                    <td className="px-4 py-2.5 text-sm text-text-secondary truncate max-w-[200px]">{emp.department}</td>
                    <td className="px-4 py-2.5 text-sm text-text-secondary">{emp.rank}</td>
                    <td className="px-4 py-2.5 text-sm text-text-secondary">{emp.grade_level}</td>
                    <td className="px-4 py-2.5 text-sm">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        (emp.status || "").toLowerCase() === "active"
                          ? "bg-badge-green-bg text-badge-green-text"
                          : "bg-nav-hover text-text-secondary"
                      }`}>
                        {emp.status}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-sm text-text-secondary">{emp.geographical_zone}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="px-4 py-3 border-t border-divider flex items-center justify-between text-sm text-text-secondary">
          <div className="flex items-center gap-2">
            <span>Rows per page:</span>
            <select
              value={size}
              onChange={(e) => { setSize(Number(e.target.value)); setPage(1); }}
              className="px-2 py-1 border border-border rounded-input bg-surface text-text-secondary text-sm cursor-pointer"
            >
              {[10, 25, 50, 100].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
            <span className="text-text-muted">
              {(page - 1) * size + 1}–{Math.min(page * size, total)} of {total.toLocaleString()}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(1)}
              disabled={page <= 1}
              className="px-2 py-1 rounded-btn border border-border text-text-secondary hover:bg-nav-hover disabled:opacity-40 disabled:cursor-not-allowed text-xs"
            >««</button>
            <button
              onClick={() => setPage(page - 1)}
              disabled={page <= 1}
              className="px-3 py-1 rounded-btn border border-border text-text-secondary hover:bg-nav-hover disabled:opacity-40 disabled:cursor-not-allowed text-xs"
            >«</button>
            <span className="px-2 text-xs">{page} / {totalPages}</span>
            <button
              onClick={() => setPage(page + 1)}
              disabled={page >= totalPages}
              className="px-3 py-1 rounded-btn border border-border text-text-secondary hover:bg-nav-hover disabled:opacity-40 disabled:cursor-not-allowed text-xs"
            >»</button>
            <button
              onClick={() => setPage(totalPages)}
              disabled={page >= totalPages}
              className="px-2 py-1 rounded-btn border border-border text-text-secondary hover:bg-nav-hover disabled:opacity-40 disabled:cursor-not-allowed text-xs"
            >»»</button>
          </div>
        </div>
      </div>

      {/* Employee Detail Drawer */}
      <AnimatePresence>
        {selectedId && (
          <>
            <motion.div
              className="fixed inset-0 bg-black/20 z-40"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedId(null)}
            />
            <motion.div
              className="fixed right-0 top-0 h-full w-[480px] max-w-[90vw] bg-surface border-l border-border z-50 flex flex-col"
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
            >
              <div className="flex items-center justify-between px-5 py-4 border-b border-divider flex-shrink-0">
                <h3 className="text-sm font-semibold text-text-primary">Employee Detail</h3>
                <button onClick={() => setSelectedId(null)} className="p-1.5 rounded-btn hover:bg-nav-hover text-text-muted hover:text-text-secondary">
                  <X size={18} />
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-5">
                {detailLoading ? (
                  <div className="space-y-3 animate-pulse">
                    {[...Array(8)].map((_, i) => (<div key={i} className="h-5 bg-nav-hover rounded" />))}
                  </div>
                ) : detail ? (
                  <div className="space-y-5">
                    <div>
                      <h4 className="text-base font-semibold text-text-primary">{detail.full_name}</h4>
                      <p className="text-sm text-text-secondary">{detail.id_no}</p>
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      {[
                        ["Department", detail.department],
                        ["Rank", detail.rank],
                        ["Grade Level", detail.grade_level],
                        ["Status", detail.status],
                        ["Employment Type", detail.employment_type],
                        ["Sex", detail.sex],
                        ["Geo Zone", detail.geographical_zone],
                        ["Phone", detail.phone_number || "—"],
                        ["Last Deployment", detail.date_of_last_deployment || "—"],
                      ].map(([label, value]) => (
                        <div key={label}>
                          <p className="text-xs text-text-muted">{label}</p>
                          <p className="text-text-primary font-medium">{value}</p>
                        </div>
                      ))}
                    </div>
                    {detail.remark && (
                      <div>
                        <p className="text-xs text-text-muted mb-1">Remark</p>
                        <p className="text-sm text-text-secondary bg-nav-hover rounded-input p-2">{detail.remark}</p>
                      </div>
                    )}

                    {detail.card_swipes.length > 0 && (
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <Clock size={14} className="text-accent" />
                          <p className="text-xs font-semibold text-text-secondary uppercase">Recent Swipes</p>
                        </div>
                        <div className="space-y-1">
                          {detail.card_swipes.slice(0, 10).map((s) => (
                            <div key={s.swipe_id} className="flex justify-between text-xs py-1.5 px-2 rounded hover:bg-nav-hover">
                              <span className="text-text-secondary">{s.location}</span>
                              <span className="text-text-primary font-mono">{s.swipe_time ? new Date(s.swipe_time).toLocaleString("en-GB") : "—"}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {detail.leave_records.length > 0 && (
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <Umbrella size={14} className="text-warning" />
                          <p className="text-xs font-semibold text-text-secondary uppercase">Recent Leave</p>
                        </div>
                        <div className="space-y-1">
                          {detail.leave_records.slice(0, 10).map((l) => (
                            <div key={l.record_id} className="flex justify-between text-xs py-1.5 px-2 rounded hover:bg-nav-hover">
                              <span className="text-text-secondary">{l.leave_type_name}</span>
                              <span className="text-text-primary font-mono">{l.start_date} – {l.end_date}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {detail.training_records.length > 0 && (
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <GraduationCap size={14} className="text-info" />
                          <p className="text-xs font-semibold text-text-secondary uppercase">Recent Training</p>
                        </div>
                        <div className="space-y-1">
                          {detail.training_records.slice(0, 10).map((t) => (
                            <div key={t.training_id} className="text-xs py-1.5 px-2 rounded hover:bg-nav-hover">
                              <p className="text-text-primary font-medium">{t.title || "Training"}</p>
                              <p className="text-text-muted">{t.venue} · {t.consultant} · {t.start_date}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-text-muted">Employee not found</p>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
