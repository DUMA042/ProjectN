import { useState, useMemo } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  createColumnHelper,
  flexRender,
  type SortingState,
} from "@tanstack/react-table";
import { ChevronUp, ChevronDown, ChevronsUpDown, Search } from "lucide-react";

interface DataTableProps<T extends object> {
  columns: { key: string; header: string; cell?: (row: T) => React.ReactNode }[];
  data: T[];
  loading?: boolean;
  searchable?: boolean;
  pageSize?: number;
}

export default function DataTable<T extends object>({
  columns: columnDefs,
  data,
  loading,
  searchable = true,
  pageSize = 25,
}: DataTableProps<T>) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState("");

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

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize } },
  });

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
      <div className="px-5 py-3 border-b border-divider flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text-primary">
          Employee Summary Report
        </h3>
        {searchable && (
          <div className="relative">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
            />
            <input
              type="text"
              placeholder="Search..."
              value={globalFilter}
              onChange={(e) => setGlobalFilter(e.target.value)}
              className="pl-9 pr-3 py-1.5 text-sm border border-border rounded-input bg-surface text-text-primary placeholder-text-muted focus:outline-none focus:border-accent transition-colors w-56"
            />
          </div>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id} className="border-b border-divider">
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className="px-4 py-2.5 text-left text-table-header text-text-muted uppercase tracking-wider cursor-pointer select-none hover:text-text-secondary transition-colors"
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    <div className="flex items-center gap-1.5">
                      {flexRender(
                        header.column.columnDef.header,
                        header.getContext()
                      )}
                      {{
                        asc: <ChevronUp size={14} />,
                        desc: <ChevronDown size={14} />,
                      }[header.column.getIsSorted() as string] ?? (
                        <ChevronsUpDown size={14} className="opacity-40" />
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            ))}
          </thead>

          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr
                key={row.id}
                className="border-b border-divider last:border-0 hover:bg-nav-hover transition-colors"
              >
                {row.getVisibleCells().map((cell) => (
                  <td
                    key={cell.id}
                    className="px-4 py-2.5 text-sm text-text-primary"
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="px-5 py-3 border-t border-divider flex items-center justify-between text-sm text-text-secondary">
        <span>
          {table.getState().pagination.pageIndex * table.getState().pagination.pageSize + 1}
          {" – "}
          {Math.min(
            (table.getState().pagination.pageIndex + 1) * table.getState().pagination.pageSize,
            table.getFilteredRowModel().rows.length
          )}
          {" of "}
          {table.getFilteredRowModel().rows.length}
        </span>

        <div className="flex items-center gap-1">
          <button
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="px-3 py-1 rounded-btn border border-border text-text-secondary hover:bg-nav-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          <button
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="px-3 py-1 rounded-btn border border-border text-text-secondary hover:bg-nav-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
