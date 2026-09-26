import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, ReactNode } from "react";

type ExportFn = () => void;

interface ExportRegistryValue {
  register: (fn: ExportFn | null) => void;
  exportNow: () => void;
  hasExport: boolean;
}

const ExportCtx = createContext<ExportRegistryValue>({
  register: () => {},
  exportNow: () => {},
  hasExport: false,
});

/** Lets the active tab publish its CSV-export action to the page header. */
export function ExportProvider({ children }: { children: ReactNode }) {
  const fnRef = useRef<ExportFn | null>(null);
  const [hasExport, setHasExport] = useState(false);

  const register = useCallback((fn: ExportFn | null) => {
    fnRef.current = fn;
    setHasExport(fn != null);
  }, []);

  const exportNow = useCallback(() => {
    fnRef.current?.();
  }, []);

  const value = useMemo(() => ({ register, exportNow, hasExport }), [register, exportNow, hasExport]);
  return <ExportCtx.Provider value={value}>{children}</ExportCtx.Provider>;
}

/** Tab-side hook: register the current export action (null to unregister). */
export function useTabExport(fn: ExportFn | null) {
  const { register } = useContext(ExportCtx);
  const fnRef = useRef(fn);
  fnRef.current = fn;
  useEffect(() => {
    register(() => fnRef.current?.() ?? undefined);
    return () => register(null);
  }, [register]);
}

export function useExportButton() {
  return useContext(ExportCtx);
}
