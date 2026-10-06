import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";

export type ToastKind = "success" | "warning" | "error" | "info";

interface ToastItem {
  id: number;
  message: string;
  kind: ToastKind;
}

interface ToastCtxValue {
  toast: (message: string, kind?: ToastKind) => void;
}

const ToastCtx = createContext<ToastCtxValue>({ toast: () => {} });

export function useToast() {
  return useContext(ToastCtx);
}

const KIND_STYLES: Record<ToastKind, string> = {
  success: "border-badge-green-text/30 bg-surface text-text-primary",
  warning: "border-warning/40 bg-surface text-text-primary",
  error: "border-danger/40 bg-surface text-text-primary",
  info: "border-border bg-surface text-text-primary",
};

/** App-level toasts (top-right) for actions fired from any page. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const idRef = useRef(1);

  const toast = useCallback((message: string, kind: ToastKind = "info") => {
    const id = idRef.current++;
    setItems((prev) => [...prev.slice(-3), { id, message, kind }]);
    window.setTimeout(() => {
      setItems((prev) => prev.filter((t) => t.id !== id));
    }, 3500);
  }, []);

  const value = useMemo(() => ({ toast }), [toast]);

  return (
    <ToastCtx.Provider value={value}>
      {children}
      <div className="fixed top-4 right-4 z-[70] space-y-2 w-96 max-w-[90vw]">
        {items.map((t) => (
          <div
            key={t.id}
            className={`flex items-start gap-2 px-4 py-3 border rounded-card text-sm shadow-lg ${KIND_STYLES[t.kind]}`}
          >
            <span className="flex-1">{t.message}</span>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
