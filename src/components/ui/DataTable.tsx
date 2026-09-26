import { useState, useMemo, useRef, useEffect } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  createColumnHelper,
  flexRender,
  type SortingState,
  type Updater,
} from "@tanstack/react-table";
import { ChevronUp, ChevronDown, ChevronsUpDown, Search, Download, X, Filter, ChevronLeft, ChevronRight } from "lucide-react";
import { exportToCSV } from "@/lib/csvExport";
import ColumnFilterDropdown from "@/components/ui/ColumnFilterDropdown";
import { MonthCalendar } from "@/components/ui/DateRangePicker";
import type { DateRange } from "@/components/ui/DateRangePicker";

export interface DateFilterValue {
  start: string;
  end: string;
}

interface DataTableProps<T extends object> {
  title?: string;
  columns: { key: string; header: string; cell?: (row: T) => React.ReactNode; sticky?: boolean; width?: number; filter?: "values" | "date"; filterable?: boolean }[];
  data: T[];
  loading?: boolean;
  searchable?: boolean;
  pageSize?: number;
  enableColumnFilters?: boolean;
  onRowClick?: (row: T) => void;
  dateRange?: DateRange;
  csvExportName?: string;
  /** Server-side mode: parent controls pagination/sort/search/filter and data is one page. */
  serverSide?: boolean;
  total?: number;
  page?: number;
  onPageChange?: (page: number) => void;
  pageSizeOptions?: number[];
  onPageSizeChange?: (size: number) => void;
  sorting?: SortingState;
  onSortingChange?: (sorting: SortingState) => void;
  search?: string;
  onSearchChange?: (search: string) => void;
  columnFilters?: Record<string, Set<string>>;
  onColumnFiltersChange?: (filters: Record<string, Set<string>>) => void;
  filterOptions?: Record<string, string[]>;
  /** Date-range filters keyed by column (columns with filter: "date"). */
  dateFilters?: Record<string, DateFilterValue | undefined>;
  onDateFiltersChange?: (filters: Record<string, DateFilterValue | undefined>) => void;
  /** Selectable bounds for date filters (e.g. the page's overall range). */
  dateFilterBounds?: { min?: string; max?: string };
  isFetching?: boolean;
  onExport?: () => void;
}

export default function DataTable<T extends object>({
  title,
  columns: columnDefs,
  data,
  loading,
  searchable = true,
  pageSize = 25,
  enableColumnFilters = false,
  onRowClick,
  dateRange,
  csvExportName,
  serverSide = false,
  total,
  page = 1,
  onPageChange,
  pageSizeOptions = [25, 50, 100],
  onPageSizeChange,
  sorting: sortingProp,
  onSortingChange,
  search: searchProp,
  onSearchChange,
  columnFilters: filtersProp,
  onColumnFiltersChange,
  filterOptions,
  dateFilters: dateFiltersProp,
  onDateFiltersChange,
  dateFilterBounds,
  isFetching,
  onExport,
}: DataTableProps<T>) {
  const [localSorting, setLocalSorting] = useState<SortingState>([]);
  const [localGlobalFilter, setLocalGlobalFilter] = useState("");
  const [localColumnFilters, setLocalColumnFilters] = useState<Record<string, Set<string>>>({});
  const [openFilterKey, setOpenFilterKey] = useState<string | null>(null);

  // Horizontal drag-to-scroll
  const scrollRef = useRef<HTMLDivElement>(null);
  const dragState = useRef({ dragging: false, moved: false, startX: 0, startScrollLeft: 0 });
  const [dragging, setDragging] = useState(false);

  // Unified controlled/uncontrolled values
  const sorting = serverSide ? sortingProp ?? [] : localSorting;
  const globalFilter = serverSide ? searchProp ?? "" : localGlobalFilter;
  const columnFilters = serverSide ? filtersProp ?? {} : localColumnFilters;

  // Cumulative left offsets + width metadata for sticky (frozen) columns
  const stickyOffsets = useMemo(() => {
    const offsets: Record<string, number> = {};
    let left = 0;
    for (const col of columnDefs) {
      if (col.sticky) {
        offsets[col.key] = left;
        left += col.width ?? 160;
      }
    }
    return offsets;
  }, [columnDefs]);

  const colMeta = useMemo(() => {
    const m: Record<string, { sticky?: boolean; width?: number }> = {};
    for (const c of columnDefs) m[c.key] = { sticky: c.sticky, width: c.width };
    return m;
  }, [columnDefs]);

  const stickyStyle = (colKey: string, isHeader: boolean): React.CSSProperties => {
    const meta = colMeta[colKey];
    if (meta?.sticky) {
      const s: React.CSSProperties = {
        position: "sticky",
        left: stickyOffsets[colKey],
        zIndex: isHeader ? 40 : 20,
        backgroundColor: "var(--surface, #FFFFFF)",
      };
      if (isHeader) s.top = 0;
      if (meta.width) {
        s.width = meta.width;
        s.minWidth = meta.width;
        s.maxWidth = meta.width;
      }
      return s;
    }
    if (isHeader) {
      return { position: "sticky", top: 0, zIndex: 30, backgroundColor: "var(--surface, #FFFFFF)" };
    }
    return {};
  };

  const startDrag = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target.closest('button, input, select, a, [role="checkbox"], .no-drag')) return;
    const el = scrollRef.current;
    if (!el) return;
    dragState.current = {
      dragging: true,
      moved: false,
      startX: e.clientX,
      startScrollLeft: el.scrollLeft,
    };
  };

  const onDrag = (e: React.MouseEvent) => {
    const el = scrollRef.current;
    if (!el || !dragState.current.dragging) return;
    const dx = e.clientX - dragState.current.startX;
    if (Math.abs(dx) > 4) {
      dragState.current.moved = true;
      setDragging(true);
    }
    el.scrollLeft = dragState.current.startScrollLeft - dx;
  };

  const endDrag = () => {
    dragState.current.dragging = false;
    setDragging(false);
  };

  const handleContainerClickCapture = (e: React.MouseEvent) => {
    if (dragState.current.moved) {
      e.stopPropagation();
      e.preventDefault();
      dragState.current.moved = false;
    }
  };

  const columnHelper = createColumnHelper<T>();

  const columns = useMemo(
    () =>
      columnDefs.map((col) =>
        columnHelper.accessor(col.key as any, {
          header: col.header,
          cell: col.cell
            ? (info) => col.cell!(info.row.original)
            : (info) => {
                const val = info.getValue();
                return val != null ? String(val) : "—";
              },
        })
      ),
    [columnDefs]
  );

  // Unique values per column for dropdown (client mode derives them from data)
  const uniqueValuesMap = useMemo(() => {
    if (serverSide) return filterOptions || {};
    const map: Record<string, string[]> = {};
    for (const col of columnDefs) {
      const vals = new Set<string>();
      for (const row of data) {
        const v = String((row as any)[col.key] ?? "");
        if (v) vals.add(v);
      }
      map[col.key] = [...vals].sort((a, b) => a.localeCompare(b));
    }
    return map;
  }, [data, columnDefs, serverSide, filterOptions]);

  // Client-side derived data (filters + search). In server mode the server already did this.
  const filteredData = useMemo(() => {
    if (serverSide) return data;
    let rows = [...data];
    for (const [key, set] of Object.entries(columnFilters)) {
      if (set.size === 0) continue;
      rows = rows.filter((row) => set.has(String((row as any)[key] ?? "")));
    }
    if (globalFilter.trim()) {
      const q = globalFilter.toLowerCase();
      rows = rows.filter((row) =>
        Object.values(row as any).some((v) => String(v ?? "").toLowerCase().includes(q))
      );
    }
    return rows;
  }, [data, columnFilters, globalFilter, serverSide]);

  const handleSortingChange = (updater: Updater<SortingState>) => {
    const next = typeof updater === "function" ? updater(sorting) : updater;
    if (serverSide) onSortingChange?.(next);
    else setLocalSorting(next);
  };

  const applyColumnFilter = (key: string, selected: Set<string>) => {
    const next = { ...columnFilters };
    if (selected.size === 0) delete next[key];
    else next[key] = selected;
    if (serverSide) onColumnFiltersChange?.(next);
    else setLocalColumnFilters(next);
  };

  const clearAllFilters = () => {
    if (serverSide) onColumnFiltersChange?.({});
    else setLocalColumnFilters({});
    if (serverSide) onDateFiltersChange?.({});
  };

  const applyDateFilter = (key: string, value: DateFilterValue | undefined) => {
    const next = { ...(dateFiltersProp || {}) };
    if (!value) delete next[key];
    else next[key] = value;
    onDateFiltersChange?.(next);
  };

  const table = useReactTable({
    data: filteredData,
    columns,
    state: { sorting },
    onSortingChange: handleSortingChange,
    getCoreRowModel: getCoreRowModel(),
    ...(serverSide
      ? { manualSorting: true, manualFiltering: true }
      : {
          getSortedRowModel: getSortedRowModel(),
          getFilteredRowModel: getFilteredRowModel(),
          getPaginationRowModel: getPaginationRowModel(),
          initialState: { pagination: { pageSize } },
        }),
  });

  const hasActiveFilters =
    Object.values(columnFilters).some((s) => s.size > 0) ||
    Object.values(dateFiltersProp || {}).some(Boolean);

  // Pagination numbers
  const totalRows = serverSide ? total ?? data.length : table.getFilteredRowModel().rows.length;
  const currentPage = serverSide ? page : table.getState().pagination.pageIndex + 1;
  const currentPageSize = serverSide ? pageSize : table.getState().pagination.pageSize;
  const pageCount = Math.max(1, Math.ceil(totalRows / (currentPageSize || 1)));
  const rangeStart = totalRows === 0 ? 0 : (currentPage - 1) * currentPageSize + 1;
  const rangeEnd = Math.min(currentPage * currentPageSize, totalRows);
  const canPrev = currentPage > 1;
  const canNext = currentPage < pageCount;

  const goPrev = () => (serverSide ? onPageChange?.(currentPage - 1) : table.previousPage());
  const goNext = () => (serverSide ? onPageChange?.(currentPage + 1) : table.nextPage());

  const rows = table.getRowModel().rows;

  if (loading) {
    return (
      <div className="card-container p-5 animate-pulse">
        <div className="h-5 w-48 bg-nav-hover rounded mb-4" />
        {[...Array(8)].map((_, i) => (
          <div key={i} className="flex gap-4 py-3">
            <div className="h-4 flex-1 bg-nav-hover rounded" />
            <div className="h-4 w-24 bg-nav-hover rounded" />
            <div className="h-4 w-32 bg-nav-hover rounded" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="card-container overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 border-b border-divider flex items-center justify-between flex-wrap gap-2">
        <h3 className="text-sm font-semibold text-text-primary">
          {title || "Summary Report"}
        </h3>
        <div className="flex items-center gap-2">
          {csvExportName && (
            <button
              onClick={() => (onExport ? onExport() : exportToCSV(filteredData, csvExportName, dateRange))}
              title={hasActiveFilters ? `Export filtered (${totalRows} rows)` : "Export CSV"}
              className="p-2 rounded-btn text-text-muted hover:text-accent hover:bg-nav-hover transition-colors"
              aria-label="Export CSV"
            >
              <Download size={14} />
            </button>
          )}
          {hasActiveFilters && (
            <button
              onClick={clearAllFilters}
              className="flex items-center gap-1 px-2 py-1 text-xs text-accent hover:bg-nav-hover rounded-btn transition-colors"
            >
              <X size={12} />
              Clear filters
            </button>
          )}
          {searchable && (
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
              <input
                type="text"
                placeholder="Search..."
                value={globalFilter}
                onChange={(e) =>
                  serverSide ? onSearchChange?.(e.target.value) : setLocalGlobalFilter(e.target.value)
                }
                className="pl-9 pr-3 py-1.5 text-sm border border-border rounded-input bg-surface text-text-primary placeholder-text-muted focus:outline-none focus:border-accent transition-colors w-56"
              />
            </div>
          )}
        </div>
      </div>

      {/* Table */}
      <div
        ref={scrollRef}
        onMouseDown={startDrag}
        onMouseMove={onDrag}
        onMouseUp={endDrag}
        onMouseLeave={endDrag}
        onClickCapture={handleContainerClickCapture}
        className={`overflow-auto max-h-[70vh] transition-opacity ${dragging ? "cursor-grabbing select-none" : "cursor-grab"} ${isFetching ? "opacity-60" : "opacity-100"}`}
      >
        <table className="w-full">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id} className="border-b border-divider">
                {headerGroup.headers.map((header) => {
                  const colKey = (header.column.columnDef as any).accessorKey as string | undefined;
                  const colDef = columnDefs.find((c) => c.key === colKey);
                  const isFiltered = colKey
                    ? (columnFilters[colKey]?.size ?? 0) > 0 || !!dateFiltersProp?.[colKey]
                    : false;
                  const isOpen = colKey ? openFilterKey === colKey : false;
                  return (
                    <th
                      key={header.id}
                      style={colKey ? stickyStyle(colKey, true) : { position: "sticky", top: 0, zIndex: 30, backgroundColor: "var(--surface, #FFFFFF)" }}
                      className="px-4 py-2.5 text-left text-table-header text-text-muted uppercase tracking-wider select-none whitespace-nowrap border-b border-divider bg-surface"
                    >
                      <div className="flex items-center gap-1.5">
                        <span
                          className="flex items-center gap-1.5 cursor-pointer hover:text-text-secondary transition-colors"
                          onClick={header.column.getToggleSortingHandler()}
                        >
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {{
                            asc: <ChevronUp size={14} />,
                            desc: <ChevronDown size={14} />,
                          }[header.column.getIsSorted() as string] ?? (
                            <ChevronsUpDown size={14} className="opacity-40" />
                          )}
                        </span>
                        {enableColumnFilters && colKey && colDef?.filterable !== false && (
                          <span className="relative">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setOpenFilterKey(isOpen ? null : colKey);
                              }}
                              className={`p-1 rounded hover:bg-nav-hover transition-colors ${isFiltered ? "text-accent" : "text-text-muted hover:text-text-secondary"}`}
                              aria-label={`Filter ${header.column.columnDef.header as string}`}
                              title="Filter"
                            >
                              <Filter size={12} />
                            </button>
                            {isFiltered && (
                              <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-accent" />
                            )}
                            {isOpen && colDef?.filter === "date" && (
                              <DateFilterPopover
                                header={header.column.columnDef.header as string}
                                value={dateFiltersProp?.[colKey]}
                                bounds={dateFilterBounds}
                                onApply={(v) => { applyDateFilter(colKey, v); setOpenFilterKey(null); }}
                                onClose={() => setOpenFilterKey(null)}
                              />
                            )}
                            {isOpen && colDef?.filter !== "date" && (
                              <ColumnFilterDropdown
                                columnKey={colKey}
                                header={header.column.columnDef.header as string}
                                uniqueValues={uniqueValuesMap[colKey] || []}
                                selected={columnFilters[colKey] || new Set()}
                                onApply={applyColumnFilter}
                                onClose={() => setOpenFilterKey(null)}
                              />
                            )}
                          </span>
                        )}
                      </div>
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>

          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={columnDefs.length} className="px-4 py-10 text-center text-sm text-text-muted">
                  No results{hasActiveFilters || globalFilter ? " — try adjusting filters" : ""}.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr
                  key={row.id}
                  onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                  className={`group border-b border-divider last:border-0 hover:bg-nav-hover transition-colors ${onRowClick ? "cursor-pointer" : ""}`}
                >
                  {row.getVisibleCells().map((cell) => {
                    const colKey = (cell.column.columnDef as any).accessorKey as string | undefined;
                    const isSticky = colKey ? colKey in stickyOffsets : false;
                    return (
                    <td
                      key={cell.id}
                      style={colKey ? stickyStyle(colKey, false) : undefined}
                      className={`px-4 py-2.5 text-sm text-text-primary ${isSticky ? "bg-surface group-hover:bg-nav-hover" : ""}`}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="px-5 py-3 border-t border-divider flex items-center justify-between text-sm text-text-secondary flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <span>
            {totalRows === 0 ? "0 of 0" : `${rangeStart} – ${rangeEnd} of ${totalRows}`}
          </span>
          {serverSide && (
            <label className="flex items-center gap-1.5 text-xs">
              Rows:
              <select
                value={currentPageSize}
                onChange={(e) => onPageSizeChange?.(Number(e.target.value))}
                className="px-2 py-1 text-xs border border-border rounded-btn bg-surface text-text-secondary cursor-pointer hover:bg-nav-hover"
              >
                {pageSizeOptions.map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </label>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={goPrev}
            disabled={!canPrev}
            className="px-3 py-1 rounded-btn border border-border text-text-secondary hover:bg-nav-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          <span className="px-2 text-xs">Page {currentPage} of {pageCount}</span>
          <button
            onClick={goNext}
            disabled={!canNext}
            className="px-3 py-1 rounded-btn border border-border text-text-secondary hover:bg-nav-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Date-range column filter popover ────────────────────────────────────────
function DateFilterPopover({
  header,
  value,
  bounds,
  onApply,
  onClose,
}: {
  header: string;
  value?: DateFilterValue;
  bounds?: { min?: string; max?: string };
  onApply: (value: DateFilterValue | undefined) => void;
  onClose: () => void;
}) {
  const [start, setStart] = useState(value?.start || "");
  const [end, setEnd] = useState(value?.end || "");
  const [pickingEnd, setPickingEnd] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const now = new Date();
  const [calMonth, setCalMonth] = useState({ y: now.getFullYear(), m: now.getMonth() });

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [onClose]);

  const pad = (n: number) => String(n).padStart(2, "0");
  const iso = (y: number, m: number, d: number) => `${y}-${pad(m + 1)}-${pad(d)}`;

  const dayClick = (y: number, m: number, d: number) => {
    const clicked = iso(y, m, d);
    if (!pickingEnd || !start || clicked < start) {
      setStart(clicked);
      setEnd(clicked);
      setPickingEnd(true);
    } else {
      setEnd(clicked);
      setPickingEnd(false);
    }
  };

  return (
    <div
      ref={ref}
      className="absolute left-0 top-full mt-1 z-30 w-[252px] bg-surface border border-border rounded-card shadow-lg p-2.5"
      onClick={(e) => e.stopPropagation()}
    >
      <p className="text-xs font-semibold text-text-primary mb-1.5">
        {header} <span className="font-normal text-text-muted">· within selected range</span>
      </p>
      <MonthCalendar
        year={calMonth.y} month={calMonth.m}
        customStart={start} customEnd={end}
        minDate={bounds?.min} maxDate={bounds?.max}
        onPrev={() => setCalMonth((p) => { const d = new Date(p.y, p.m - 1, 1); return { y: d.getFullYear(), m: d.getMonth() }; })}
        onNext={() => setCalMonth((p) => { const d = new Date(p.y, p.m + 1, 1); return { y: d.getFullYear(), m: d.getMonth() }; })}
        onDayClick={dayClick}
      />
      <div className="text-[11px] text-text-secondary text-center py-1.5">
        {start && end ? `${start} → ${end}` : "Pick a start, then an end"}
      </div>
      <div className="flex items-center justify-between pt-1.5 border-t border-divider">
        <button
          onClick={() => { setStart(""); setEnd(""); setPickingEnd(false); onApply(undefined); }}
          className="text-xs text-text-muted hover:text-text-primary px-2 py-1 rounded-btn hover:bg-nav-hover transition-colors"
        >
          Clear
        </button>
        <button
          onClick={() => start && end && onApply({ start, end })}
          disabled={!start || !end}
          className="text-xs font-medium text-white bg-accent px-3 py-1 rounded-btn hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Apply
        </button>
      </div>
    </div>
  );
}
