import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { DateRange } from "@/components/ui/DateRangePicker";

function defaultRange(): DateRange {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 89);
  const iso = (d: Date) => d.toISOString().split("T")[0];
  return { startDate: iso(start), endDate: iso(end), label: "Last 90 Days" };
}

export type ManagementTab = "pulse" | "trends" | "explore" | "people" | "forecast";

export interface SavedView {
  name: string;
  tab: ManagementTab;
  location: string | null;
  dateRange: DateRange;
  compare: boolean;
  filters: Record<string, string[]>;
}

interface ManagementScopeState {
  tab: ManagementTab;
  /** Selected location name, or null for All Locations. */
  location: string | null;
  dateRange: DateRange;
  compare: boolean;
  /** Dimension filters (scope chips), excluding location. */
  filters: Record<string, string[]>;
  savedViews: SavedView[];
  /** People tab entity mode ("individuals" or a group dimension key). */
  peopleEntity: "individuals" | "department" | "grade_level" | "rank" | "employment_type" | "zone";

  setTab: (tab: ManagementTab) => void;
  setLocation: (location: string | null) => void;
  setDateRange: (range: DateRange) => void;
  setCompare: (compare: boolean) => void;
  setPeopleEntity: (entity: ManagementScopeState["peopleEntity"]) => void;
  setFilter: (dimension: string, values: string[]) => void;
  /** Drill helper: add one value to a dimension filter. */
  addFilter: (dimension: string, value: string) => void;
  removeFilter: (dimension: string, value: string) => void;
  removeDimension: (dimension: string) => void;
  clearFilters: () => void;
  saveView: (name: string) => void;
  applyView: (name: string) => void;
  deleteView: (name: string) => void;
}

export const useManagementScope = create<ManagementScopeState>()(
  persist(
    (set, get) => ({
      tab: "pulse",
      location: null,
      dateRange: defaultRange(),
      compare: false,
      filters: {},
      savedViews: [],
      peopleEntity: "individuals",

      setTab: (tab) => set({ tab }),
      setLocation: (location) => set({ location }),
      setDateRange: (dateRange) => set({ dateRange }),
      setCompare: (compare) => set({ compare }),
      setPeopleEntity: (peopleEntity) => set({ peopleEntity }),

      setFilter: (dimension, values) =>
        set((s) => {
          const next = { ...s.filters };
          if (values.length === 0) delete next[dimension];
          else next[dimension] = values;
          return { filters: next };
        }),

      addFilter: (dimension, value) =>
        set((s) => {
          const cur = new Set(s.filters[dimension] || []);
          cur.add(value);
          return { filters: { ...s.filters, [dimension]: [...cur] } };
        }),

      removeFilter: (dimension, value) =>
        set((s) => {
          const cur = (s.filters[dimension] || []).filter((v) => v !== value);
          const next = { ...s.filters };
          if (cur.length === 0) delete next[dimension];
          else next[dimension] = cur;
          return { filters: next };
        }),

      removeDimension: (dimension) =>
        set((s) => {
          const next = { ...s.filters };
          delete next[dimension];
          return { filters: next };
        }),

      clearFilters: () => set({ filters: {} }),

      saveView: (name) =>
        set((s) => {
          const view: SavedView = {
            name,
            tab: s.tab,
            location: s.location,
            dateRange: s.dateRange,
            compare: s.compare,
            filters: s.filters,
          };
          const others = s.savedViews.filter((v) => v.name !== name);
          return { savedViews: [...others, view] };
        }),

      applyView: (name) => {
        const view = get().savedViews.find((v) => v.name === name);
        if (view) {
          set({
            tab: view.tab,
            location: view.location,
            dateRange: view.dateRange,
            compare: view.compare,
            filters: view.filters,
          });
        }
      },

      deleteView: (name) =>
        set((s) => ({ savedViews: s.savedViews.filter((v) => v.name !== name) })),
    }),
    {
      name: "management-scope",
      // v2: sanitize any state persisted by older builds so a stale shape can
      // never crash the page on load.
      version: 2,
      migrate: (persisted: unknown) => {
        const p = (persisted || {}) as Record<string, unknown>;
        const dr = p.dateRange as { startDate?: unknown; endDate?: unknown; label?: unknown } | undefined;
        return {
          tab: typeof p.tab === "string" ? p.tab : "pulse",
          location: typeof p.location === "string" ? p.location : null,
          dateRange:
            dr && typeof dr.startDate === "string" && typeof dr.endDate === "string" && typeof dr.label === "string"
              ? (dr as DateRange)
              : defaultRange(),
          compare: !!p.compare,
          filters:
            p.filters && typeof p.filters === "object" && !Array.isArray(p.filters)
              ? (p.filters as Record<string, string[]>)
              : {},
          savedViews: Array.isArray(p.savedViews) ? (p.savedViews as SavedView[]) : [],
          peopleEntity: typeof p.peopleEntity === "string" ? p.peopleEntity : "individuals",
        };
      },
      partialize: (s) => ({
        tab: s.tab,
        location: s.location,
        dateRange: s.dateRange,
        compare: s.compare,
        filters: s.filters,
        savedViews: s.savedViews,
        peopleEntity: s.peopleEntity,
      }),
    }
  )
);

/** Full API filters for the active scope: dimension chips + location merged. */
export function scopeToApiFilters(
  filters: Record<string, string[]>,
  location: string | null
): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const [k, v] of Object.entries(filters)) {
    if (v.length > 0) out[k] = v;
  }
  if (location) out["location"] = [location];
  return out;
}
