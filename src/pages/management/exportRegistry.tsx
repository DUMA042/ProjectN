import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, ReactNode } from "react";

/** Row descriptor feeding Export CSV + Send to Report for the active tab. */
export interface TabExportDescriptor {
  getRows: () => Record<string, unknown>[] | Promise<Record<string, unknown>[]>;
  fileName: string;
  dateRange?: { startDate?: string; endDate?: string };
  source?: string;
}

interface ExportRegistryValue {
  register: (desc: TabExportDescriptor | null) => void;
  descriptor: TabExportDescriptor | null;
  hasExport: boolean;
}

const ExportCtx = createContext<ExportRegistryValue>({
  register: () => {},
  descriptor: null,
  hasExport: false,
});

/** Lets the active tab publish its exportable dataset to the page header. */
export function ExportProvider({ children }: { children: ReactNode }) {
  const descRef = useRef<TabExportDescriptor | null>(null);
  const [descriptor, setDescriptor] = useState<TabExportDescriptor | null>(null);

  const register = useCallback((desc: TabExportDescriptor | null) => {
    descRef.current = desc;
    setDescriptor(desc);
  }, []);

  const value = useMemo(() => ({ register, descriptor, hasExport: descriptor != null }), [register, descriptor]);
  return <ExportCtx.Provider value={value}>{children}</ExportCtx.Provider>;
}

/** Tab-side hook: register the current export dataset (null to unregister). */
export function useTabExport(desc: TabExportDescriptor | null) {
  const { register } = useContext(ExportCtx);
  const descRef = useRef(desc);
  descRef.current = desc;
  useEffect(() => {
    register(descRef.current);
    return () => register(null);
  }, [register]);
}

export function useExportButton() {
  return useContext(ExportCtx);
}
