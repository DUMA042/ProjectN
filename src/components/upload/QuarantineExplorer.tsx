import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, Trash2, RefreshCw, Download,
  ChevronLeft, ChevronRight, ShieldAlert,
} from "lucide-react";
import {
  useQuarantineList,
  useDeleteQuarantine,
  useReprocessQuarantine,
} from "@/hooks/useIngestion";
import type { QuarantineType, QuarantineRow } from "@/hooks/useIngestion";

interface QuarantineExplorerProps {
  onToast: (message: string, kind: "success" | "warning" | "error" | "info") => void;
}

const PAGE_SIZE = 50;

export default function QuarantineExplorer({ onToast }: QuarantineExplorerProps) {
  const [tab, setTab] = useState<QuarantineType>("swipes");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Set<number>>(new Set());

  const listQuery = useQuarantineList({
    type: tab, search, startDate, endDate, page, size: PAGE_SIZE,
  });
  const deleteMutation = useDeleteQuarantine();
  const reprocessMutation = useReprocessQuarantine();

  const rows = listQuery.data?.rows || [];
  const total = listQuery.data?.total || 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const applySearch = () => {
    setSearch(searchInput);
    setPage(1);
  };

  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === rows.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(rows.map((r) => r.id)));
    }
  };

  const runBulk = async (action: "delete" | "reprocess") => {
    if (!selected.size) return;
    try {
      if (action === "delete") {
        const res = await deleteMutation.mutateAsync({ type: tab, ids: [...selected] });
        onToast(`🗑 ${res.deleted} quarantined record(s) permanently deleted.`, "success");
      } else {
        const res = await reprocessMutation.mutateAsync({ type: tab, ids: [...selected] });
        if (res.failed_count > 0) {
          onToast(
            `♻️ Reprocessed: ${res.succeeded} succeeded, ${res.failed_count} still unresolvable (employees missing).`,
            res.succeeded > 0 ? "warning" : "error"
          );
        } else {
          onToast(`♻️ ${res.succeeded} record(s) reprocessed into the database.`, "success");
        }
      }
      setSelected(new Set());
    } catch {
      onToast(`❌ Bulk ${action} failed — check that the API server is running.`, "error");
    }
  };

  const runSingleReprocess = async (row: QuarantineRow) => {
    try {
      const res = await reprocessMutation.mutateAsync({ type: tab, ids: [row.id] });
      if (res.failed_count > 0 && res.succeeded === 0) {
        onToast(`⚠️ ${row.employee_name || row.row_key}: ${res.failures[0]?.error || "Still unresolvable."}`, "warning");
      } else {
        onToast(`♻️ Record for '${row.employee_name || row.row_key}' moved into the database.`, "success");
      }
    } catch {
      onToast("❌ Reprocess failed.", "error");
    }
  };

  const runSingleDelete = async (row: QuarantineRow) => {
    try {
      const res = await deleteMutation.mutateAsync({ type: tab, ids: [row.id] });
      onToast(`🗑 Record deleted (${res.deleted}).`, "success");
    } catch {
      onToast("❌ Delete failed.", "error");
    }
  };

  const exportCsv = () => {
    if (!rows.length) return;
    const isSwipes = tab === "swipes";
    const header = isSwipes
      ? ["Employee Name", "ID Hint", "Location", "Swipe Time", "Quarantined At"]
      : ["ID No", "Venue", "Consultant", "Title", "Start Date", "End Date", "Quarantined At"];
    const esc = (v: any) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const lines = [header.join(",")];
    for (const r of rows) {
      lines.push(
        isSwipes
          ? [r.employee_name, r.row_key, r.location, r.event_time, r.quarantined_at].map(esc).join(",")
          : [r.row_key, r.venue, r.consultant, r.title, r.start_date, r.end_date, r.quarantined_at].map(esc).join(",")
      );
    }
    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `quarantined_${tab}_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    onToast(`⬇ Exported ${rows.length} filtered quarantined rows to CSV.`, "info");
  };

  return (
    <div className="card-container overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-divider flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <ShieldAlert size={16} className="text-warning" />
          <h3 className="text-sm font-semibold text-text-primary">Quarantined Records</h3>
          <span className="text-xs px-2 py-0.5 rounded-full bg-badge-amber-bg text-badge-amber-text font-medium">
            {total.toLocaleString()} total
          </span>
        </div>
        <div className="flex items-center gap-1 border border-border rounded-btn p-0.5">
          {(["swipes", "trainings"] as QuarantineType[]).map((t) => (
            <button
              key={t}
              onClick={() => { setTab(t); setPage(1); setSelected(new Set()); }}
              className={`px-3 py-1 text-xs rounded-md transition-colors ${
                tab === t ? "bg-accent text-white font-medium" : "text-text-secondary hover:bg-nav-hover"
              }`}
            >
              {t === "swipes" ? "Card Swipes" : "Trainings"}
            </button>
          ))}
        </div>
      </div>

      {/* Filters */}
      <div className="px-4 py-2.5 border-b border-divider flex items-center gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[180px] max-w-[280px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            placeholder={tab === "swipes" ? "Search name or location…" : "Search ID, venue…"}
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && applySearch()}
            className="w-full pl-9 pr-3 py-1.5 text-xs border border-border rounded-input bg-surface text-text-primary placeholder-text-muted focus:outline-none focus:border-accent"
          />
        </div>
        <input
          type="date"
          value={startDate}
          onChange={(e) => { setStartDate(e.target.value); setPage(1); }}
          className="px-2 py-1.5 text-xs border border-border rounded-input bg-surface text-text-secondary"
        />
        <span className="text-text-muted text-xs">→</span>
        <input
          type="date"
          value={endDate}
          onChange={(e) => { setEndDate(e.target.value); setPage(1); }}
          className="px-2 py-1.5 text-xs border border-border rounded-input bg-surface text-text-secondary"
        />
        <button onClick={applySearch} className="px-3 py-1.5 text-xs rounded-btn bg-accent text-white hover:bg-accent-hover transition-colors">
          Apply
        </button>
        <div className="ml-auto flex items-center gap-2">
          {listQuery.isFetching && <RefreshCw size={12} className="animate-spin text-text-muted" />}
          <button
            onClick={exportCsv}
            disabled={!rows.length}
            className="flex items-center gap-1 px-3 py-1.5 text-xs border border-border rounded-btn text-text-secondary hover:bg-nav-hover disabled:opacity-40 transition-colors"
          >
            <Download size={12} />
            Export CSV
          </button>
        </div>
      </div>

      {/* Bulk action bar */}
      <AnimatePresence>
        {selected.size > 0 && (
          <motion.div
            className="px-4 py-2.5 bg-[#E6F4FF] border-b border-info/30 flex items-center gap-3"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
          >
            <span className="text-xs font-medium text-accent">{selected.size} selected</span>
            <button
              onClick={() => runBulk("reprocess")}
              disabled={reprocessMutation.isPending}
              className="flex items-center gap-1 px-3 py-1 text-xs font-medium rounded-btn bg-success text-white hover:opacity-90 disabled:opacity-50"
            >
              ♻️ Reprocess selected ({selected.size})
            </button>
            <button
              onClick={() => runBulk("delete")}
              disabled={deleteMutation.isPending}
              className="flex items-center gap-1 px-3 py-1 text-xs font-medium rounded-btn bg-danger text-white hover:opacity-90 disabled:opacity-50"
            >
              <Trash2 size={12} />
              Delete selected ({selected.size})
            </button>
            <button
              onClick={() => setSelected(new Set())}
              className="ml-auto text-xs text-text-muted hover:text-text-secondary"
            >
              Clear selection
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Table */}
      {listQuery.isLoading ? (
        <div className="p-4 space-y-2 animate-pulse">
          {[...Array(6)].map((_, i) => (<div key={i} className="h-9 bg-nav-hover rounded-btn" />))}
        </div>
      ) : rows.length === 0 ? (
        <div className="p-8 text-center">
          <ShieldAlert size={32} className="mx-auto text-text-muted mb-2" strokeWidth={1.5} />
          <p className="text-sm text-text-muted">
            {search || startDate || endDate
              ? "No quarantined records match your filters."
              : "No quarantined records — everything loaded cleanly."}
          </p>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-divider bg-surface">
                  <th className="px-3 py-2 w-8">
                    <input
                      type="checkbox"
                      checked={selected.size === rows.length && rows.length > 0}
                      onChange={toggleSelectAll}
                      className="cursor-pointer accent-[#1677FF]"
                    />
                  </th>
                  {tab === "swipes" ? (
                    <>
                      <th className="text-left px-3 py-2 text-xs text-text-muted font-semibold uppercase">Employee Name</th>
                      <th className="text-left px-3 py-2 text-xs text-text-muted font-semibold uppercase w-24">ID Hint</th>
                      <th className="text-left px-3 py-2 text-xs text-text-muted font-semibold uppercase w-28">Location</th>
                      <th className="text-left px-3 py-2 text-xs text-text-muted font-semibold uppercase w-36">Swipe Time</th>
                    </>
                  ) : (
                    <>
                      <th className="text-left px-3 py-2 text-xs text-text-muted font-semibold uppercase w-24">ID No</th>
                      <th className="text-left px-3 py-2 text-xs text-text-muted font-semibold uppercase">Title</th>
                      <th className="text-left px-3 py-2 text-xs text-text-muted font-semibold uppercase w-32">Venue</th>
                      <th className="text-left px-3 py-2 text-xs text-text-muted font-semibold uppercase w-28">Dates</th>
                    </>
                  )}
                  <th className="text-left px-3 py-2 text-xs text-text-muted font-semibold uppercase w-40">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id} className="border-b border-divider last:border-0 hover:bg-nav-hover transition-colors">
                    <td className="px-3 py-2">
                      <input
                        type="checkbox"
                        checked={selected.has(r.id)}
                        onChange={() => toggleSelect(r.id)}
                        className="cursor-pointer accent-[#1677FF]"
                      />
                    </td>
                    {tab === "swipes" ? (
                      <>
                        <td className="px-3 py-2 text-text-primary truncate max-w-[200px]" title={r.employee_name || ""}>
                          {r.employee_name || "—"}
                        </td>
                        <td className="px-3 py-2 text-text-secondary font-mono text-xs">{r.row_key || "—"}</td>
                        <td className="px-3 py-2 text-text-secondary">{r.location || "—"}</td>
                        <td className="px-3 py-2 text-text-secondary text-xs whitespace-nowrap">
                          {r.event_time ? new Date(r.event_time).toLocaleString("en-GB") : "—"}
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="px-3 py-2 text-text-primary font-mono text-xs">{r.row_key || "—"}</td>
                        <td className="px-3 py-2 text-text-primary truncate max-w-[160px]">{r.title || "Training"}</td>
                        <td className="px-3 py-2 text-text-secondary truncate max-w-[120px]">{r.venue || "—"}</td>
                        <td className="px-3 py-2 text-text-secondary text-xs whitespace-nowrap">
                          {r.start_date ? `${r.start_date} → ${r.end_date || "?"}` : "—"}
                        </td>
                      </>
                    )}
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2 opacity-70 group-hover:opacity-100">
                        <button
                          onClick={() => runSingleReprocess(r)}
                          disabled={reprocessMutation.isPending}
                          title="Try to resolve and load this record into the database"
                          className="flex items-center gap-1 text-xs text-success hover:underline disabled:opacity-40"
                        >
                          ♻️ Reprocess
                        </button>
                        <button
                          onClick={() => runSingleDelete(r)}
                          disabled={deleteMutation.isPending}
                          title="Permanently delete this quarantined record"
                          className="flex items-center gap-1 text-xs text-danger hover:underline disabled:opacity-40"
                        >
                          <Trash2 size={11} /> Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="px-4 py-2.5 border-t border-divider flex items-center justify-between text-xs text-text-secondary">
            <span>{total.toLocaleString()} quarantined records</span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage(page - 1)}
                disabled={page <= 1}
                className="p-1 rounded-btn border border-border hover:bg-nav-hover disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronLeft size={14} />
              </button>
              <span className="px-2">Page {page} of {totalPages.toLocaleString()}</span>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page >= totalPages}
                className="p-1 rounded-btn border border-border hover:bg-nav-hover disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
