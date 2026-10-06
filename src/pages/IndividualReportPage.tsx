import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useQueryClient } from "@tanstack/react-query";
import { Download, FileText, Trash2, Users } from "lucide-react";
import { useToast } from "@/components/ui/Toast";
import ConfirmCard from "@/components/ui/ConfirmCard";
import DateRangePicker from "@/components/ui/DateRangePicker";
import BuildProgress from "@/components/reports/BuildProgress";
import {
  buildIndividualReport,
  cancelIndividualBuild,
  searchStaff,
  useDepartments,
  useIndividualReports,
  useLocations,
  type EmployeeOption,
  type IndividualBuildResult,
} from "@/lib/individualReport";
import { useBuildJob } from "@/lib/reportBuild";
import { api } from "@/lib/api";

function monthBounds(): { startDate: string; endDate: string; label: string } {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  return { startDate: iso(start), endDate: iso(end), label: "This month" };
}

export default function IndividualReportPage() {
  const { toast } = useToast();
  const qc = useQueryClient();
  const [location, setLocation] = useState("");
  const [departments, setDepartments] = useState<string[]>([]);
  const [picked, setPicked] = useState<Map<string, EmployeeOption>>(new Map());
  const [pickAll, setPickAll] = useState(true);
  const [search, setSearch] = useState("");
  const [pool, setPool] = useState<EmployeeOption[]>([]);
  const [poolTotal, setPoolTotal] = useState(0);
  const [range, setRange] = useState(monthBounds);
  const [building, setBuilding] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);
  const [result, setResult] = useState<IndividualBuildResult | null>(null);
  const [pendingDelete, setPendingDelete] = useState<{ job_id: string; label: string } | null>(null);
  const [deleting, setDeleting] = useState(false);

  const locations = useLocations();
  const deptQuery = useDepartments(location);
  const deptOptions: string[] = deptQuery.data || [];
  const buildJob = useBuildJob(jobId, polling);
  const library = useIndividualReports();

  // Employee pool follows location + department + search (debounced).
  // Multi-department totals are summed per department so "All (N)" is exact.
  useEffect(() => {
    let live = true;
    const t = setTimeout(() => {
      const depts = departments.length > 0 ? departments : [""];
      Promise.all(depts.map((d) => searchStaff(search, d, location, 1, 50))).then((rs) => {
        if (!live) return;
        const total = rs.reduce((n, r) => n + r.total, 0);
        const merged: EmployeeOption[] = [];
        const seen = new Set<string>();
        for (const r of rs) {
          for (const e of r.items) {
            if (merged.length >= 200 || seen.has(e.id_no)) continue;
            seen.add(e.id_no);
            merged.push(e);
          }
        }
        setPool(merged);
        setPoolTotal(total);
      });
    }, 300);
    return () => {
      live = false;
      clearTimeout(t);
    };
  }, [search, departments, location]);

  const [suggestOpen, setSuggestOpen] = useState(false);
  const suggestions = useMemo(() => pool.filter((e) => !picked.has(e.id_no)).slice(0, 8), [pool, picked]);

  const addPerson = (e: EmployeeOption) => {
    setPicked((m) => new Map(m).set(e.id_no, e));
    setPickAll(false);
  };

  // Labels always describe the request: All+search builds the matches,
  // Selected builds the picks — never the whole scope by accident.
  const buildCount = pickAll ? poolTotal : picked.size;

  const toggleDept = (d: string) =>
    setDepartments((ds) => (ds.includes(d) ? ds.filter((x) => x !== d) : [...ds, d]));

  const onGenerate = async () => {
    if (building) return;
    if (!pickAll && picked.size === 0) {
      toast("Select at least one individual (or keep All selected)", "error");
      return;
    }
    if (typeof navigator !== "undefined" && !navigator.onLine) {
      toast("You appear to be offline — reconnect and retry.", "error");
      return;
    }
    setBuilding(true);
    setResult(null);
    setJobId(null);
    try {
      const res = await buildIndividualReport({
        location,
        departments,
        employee_ids: pickAll ? [] : [...picked.keys()],
        search: pickAll ? search.trim() : "",
        start_date: range.startDate,
        end_date: range.endDate,
      });
      // Returns immediately: progress streams into the job via polling.
      setJobId(res.job_id);
      setPolling(true);
    } catch (err) {
      const e = err as { response?: { data?: { detail?: unknown } }; request?: unknown };
      const msg =
        e?.request && !e?.response
          ? "No connection to the server — check your internet and retry."
          : typeof e?.response?.data?.detail === "string"
            ? e.response.data.detail
            : "Report build failed";
      toast(msg, "error");
      setBuilding(false);
    }
  };

  // Settle: complete pulls the download from the job payload; failures surface.
  useEffect(() => {
    const job = buildJob.data;
    if (!job || !polling) return;
    if (job.stage === "complete") {
      setPolling(false);
      setBuilding(false);
      const r = (job.payload as { result?: { headcount: number; filename: string; download_url: string } } | undefined)?.result;
      if (r) {
        setResult({ job_id: job.id, stage: "complete", ...r });
        void qc.invalidateQueries({ queryKey: ["individual-reports"] });
        toast(`Report complete — ${r.headcount} employees`, "success");
      }
    } else if (job.stage === "failed") {
      setPolling(false);
      setBuilding(false);
      toast(job.stage_detail || "Report build failed", "error");
    } else if (job.stage === "cancelled") {
      setPolling(false);
      setBuilding(false);
    }
  }, [buildJob.data, polling, qc, toast]);

  const onCancel = async () => {
    if (!jobId || cancelling) return;
    setCancelling(true);
    try {
      await cancelIndividualBuild(jobId);
      setPolling(false);
      toast("Build cancelled", "info");
    } catch {
      toast("Could not cancel the build", "error");
    } finally {
      setCancelling(false);
    }
  };

  const onDeleteReport = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await api.delete(`/api/individual-reports/${pendingDelete.job_id}`);
      await qc.invalidateQueries({ queryKey: ["individual-reports"] });
      toast("Report deleted", "success");
      setPendingDelete(null);
    } catch {
      toast("Could not delete the report", "error");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <motion.div
      className="p-6 space-y-4"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Individual Report</h1>
        <p className="text-sm text-text-secondary mt-0.5">
          Per-employee daily grids and summaries — computed from live data, real names.
        </p>
      </div>

      {/* Selection */}
      <div className="card-container p-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <label className="block">
            <span className="text-xs font-medium text-text-secondary">Location</span>
            <select
              value={location}
              onChange={(e) => {
                setLocation(e.target.value);
                setDepartments([]);
                setPicked(new Map());
                setPickAll(true);
              }}
              className="mt-1 w-full px-2 py-1.5 text-sm rounded-btn border border-border bg-surface text-text-primary"
            >
              <option value="">All locations</option>
              {(locations.data || []).map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </label>
          <div className="md:col-span-2">
            <span className="text-xs font-medium text-text-secondary">Date range</span>
            <div className="mt-1">
              <DateRangePicker value={range} onChange={setRange} />
            </div>
          </div>
        </div>

        <div>
          <span className="text-xs font-medium text-text-secondary">
            Departments {departments.length > 0 && `(${departments.length} selected)`}
          </span>
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {deptOptions.length === 0 && (
              <span className="text-[11px] text-text-muted">No departments found.</span>
            )}
            {deptOptions.map((d) => (
              <button
                key={d}
                onClick={() => toggleDept(d)}
                className={`px-2.5 py-1 text-[11px] rounded-btn border transition-colors ${
                  departments.includes(d)
                    ? "border-accent text-accent bg-accent/5"
                    : "border-border text-text-secondary hover:bg-nav-hover"
                }`}
              >
                {d}
              </button>
            ))}
            {departments.length > 0 && (
              <button
                onClick={() => setDepartments([])}
                className="px-2.5 py-1 text-[11px] rounded-btn border border-border text-text-muted hover:bg-nav-hover transition-colors"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-medium text-text-secondary flex items-center gap-1">
              <Users size={13} /> Individuals
            </span>
            <button
              onClick={() => setPickAll(true)}
              className={`px-2.5 py-1 text-[11px] rounded-btn border transition-colors ${
                pickAll ? "border-accent text-accent bg-accent/5" : "border-border text-text-secondary hover:bg-nav-hover"
              }`}
            >
              All ({poolTotal})
            </button>
            <button
              onClick={() => setPickAll(false)}
              className={`px-2.5 py-1 text-[11px] rounded-btn border transition-colors ${
                !pickAll ? "border-accent text-accent bg-accent/5" : "border-border text-text-secondary hover:bg-nav-hover"
              }`}
            >
              Selected ({picked.size})
            </button>
            <div className="relative ml-auto">
              <input
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setSuggestOpen(true);
                }}
                onFocus={() => setSuggestOpen(true)}
                onBlur={() => setTimeout(() => setSuggestOpen(false), 150)}
                placeholder="Search name or ID…"
                aria-label="Search staff by name or ID"
                className="px-2 py-1 text-xs rounded-btn border border-border bg-surface text-text-primary w-44"
              />
              {suggestOpen && search.trim() && suggestions.length > 0 && (
                <ul className="absolute right-0 z-20 mt-1 w-64 max-h-56 overflow-y-auto card-container rounded-btn border border-border shadow-lg">
                  {suggestions.map((e) => (
                    <li key={e.id_no}>
                      <button
                        onMouseDown={(ev) => ev.preventDefault()}
                        onClick={() => {
                          addPerson(e);
                          setSuggestOpen(false);
                        }}
                        className="w-full flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-nav-hover text-left"
                      >
                        <span className="font-medium text-text-primary truncate">{e.full_name}</span>
                        <span className="text-text-muted tabular-nums">{e.id_no}</span>
                        <span className="text-accent ml-auto flex-shrink-0">+ Add</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
          {search.trim() && pickAll && (
            <p className="text-[11px] text-text-muted mt-1">
              Search narrows All — Generate will build the {poolTotal} matching{" "}
              {poolTotal === 1 ? "person" : "people"}, not the whole scope.
            </p>
          )}
          {picked.size > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {[...picked.values()].map((e) => (
                <span
                  key={e.id_no}
                  className="inline-flex items-center gap-1 pl-2 pr-1 py-0.5 text-[11px] bg-accent/5 border border-accent/30 text-accent rounded-full"
                >
                  {e.full_name} · {e.id_no}
                  <button
                    onClick={() =>
                      setPicked((m) => {
                        const next = new Map(m);
                        next.delete(e.id_no);
                        return next;
                      })
                    }
                    aria-label={`Remove ${e.full_name}`}
                    className="px-1 hover:text-danger transition-colors"
                  >
                    ×
                  </button>
                </span>
              ))}
              <button
                onClick={() => setPicked(new Map())}
                className="text-[11px] text-text-muted hover:text-danger transition-colors"
              >
                Clear all
              </button>
            </div>
          )}
          {!pickAll && (
            <ul className="mt-2 max-h-56 overflow-y-auto border border-border rounded-btn divide-y divide-divider">
              {pool.map((e) => (
                <li key={e.id_no}>
                  <label className="flex items-center gap-2 px-3 py-1.5 text-xs cursor-pointer hover:bg-nav-hover">
                    <input
                      type="checkbox"
                      checked={picked.has(e.id_no)}
                      onChange={() =>
                        setPicked((m) => {
                          const next = new Map(m);
                          if (next.has(e.id_no)) next.delete(e.id_no);
                          else next.set(e.id_no, e);
                          return next;
                        })
                      }
                      className="accent-[#1677FF]"
                    />
                    <span className="font-medium text-text-primary truncate">{e.full_name}</span>
                    <span className="text-text-muted tabular-nums">{e.id_no}</span>
                    <span className="text-text-muted ml-auto truncate">{e.department}</span>
                  </label>
                </li>
              ))}
              {pool.length === 0 && (
                <li className="px-3 py-3 text-xs text-text-muted">No matching staff.</li>
              )}
            </ul>
          )}
        </div>

        <button
          onClick={() => { void onGenerate(); }}
          disabled={building || (!pickAll && picked.size === 0)}
          className="w-full px-3 py-2 text-xs font-medium text-white bg-accent rounded-btn hover:opacity-90 transition-opacity disabled:opacity-40"
        >
          {building ? "Building report…" : `Generate Individual Report (${buildCount} selected)`}
        </button>
      </div>

      {/* Progress */}
      {jobId && buildJob.data ? (
        <BuildProgress
          job={buildJob.data}
          names={new Map(pool.map((e) => [e.id_no, e.full_name]))}
          classifications={new Map(pool.map((e) => [e.id_no, "non_individual"]))}
          cancellable={!["complete", "cancelled"].includes(buildJob.data.stage) && !cancelling}
          onCancel={() => { void onCancel(); }}
        />
      ) : null}

      {/* Result */}
      {result ? (
        <div className="card-container p-4 flex items-center gap-3 flex-wrap">
          <FileText size={16} className="text-accent flex-shrink-0" />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-text-primary truncate" title={result.filename}>
              {result.filename}
            </p>
            <p className="text-[11px] text-text-muted">{result.headcount} employees</p>
          </div>
          <a
            href={result.download_url}
            download
            className="px-3 py-1.5 text-xs font-medium text-white bg-accent rounded-btn hover:opacity-90 transition-opacity"
          >
            Download Word
          </a>
        </div>
      ) : null}

      {/* Library */}
      <div className="card-container overflow-hidden">
        <div className="px-4 pt-3 pb-1 flex items-center gap-2">
          <FileText size={13} className="text-text-muted" />
          <h2 className="text-xs font-semibold text-text-primary">Individual reports</h2>
          <span className="text-[11px] text-text-muted">Stored in the application</span>
        </div>
        {!library.data ? (
          <div className="p-5 space-y-2">
            <div className="h-9 bg-nav-hover rounded animate-pulse" />
          </div>
        ) : library.data.reports.length === 0 ? (
          <p className="px-4 pb-4 text-xs text-text-muted">
            No individual reports yet. Generated reports appear here with download and delete options.
          </p>
        ) : (
          <ul className="px-4 pb-3 space-y-1.5">
            {library.data.reports.map((r) => (
              <li
                key={r.job_id}
                className="flex items-center gap-2 p-2 rounded-btn border border-border hover:bg-nav-hover transition-colors"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-text-primary truncate" title={r.filename}>
                    {r.filename}
                  </p>
                  <p className="text-[11px] text-text-muted truncate">
                    {r.period} · {r.location} · {r.headcount} employees
                  </p>
                </div>
                <a
                  href={r.download_url}
                  download
                  title="Download Word document"
                  aria-label={`Download ${r.filename}`}
                  className="p-2 rounded-btn text-text-muted hover:text-accent hover:bg-nav-hover transition-colors"
                >
                  <Download size={14} />
                </a>
                <button
                  onClick={() => setPendingDelete({ job_id: r.job_id, label: r.filename })}
                  title="Delete this report"
                  aria-label={`Delete ${r.filename}`}
                  className="p-2 rounded-btn text-text-muted hover:text-danger hover:bg-nav-hover transition-colors"
                >
                  <Trash2 size={14} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      {pendingDelete ? (
        <ConfirmCard
          title="Delete report?"
          message={`"${pendingDelete.label}" will be removed. This cannot be undone.`}
          busy={deleting}
          onConfirm={() => { void onDeleteReport(); }}
          onCancel={() => { if (!deleting) setPendingDelete(null); }}
        />
      ) : null}
    </motion.div>
  );
}
