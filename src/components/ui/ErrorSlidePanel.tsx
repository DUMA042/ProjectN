import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";

interface FailedRow {
  row: number | string;
  id_no: string;
  field: string;
  message: string;
}

interface ErrorSlidePanelProps {
  open: boolean;
  onClose: () => void;
  filename: string;
  rows?: FailedRow[];
  loading?: boolean;
  children?: React.ReactNode;
}

export default function ErrorSlidePanel({
  open,
  onClose,
  filename,
  rows,
  loading,
  children,
}: ErrorSlidePanelProps) {
  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 bg-black/20 z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            className="fixed right-0 top-0 h-full w-[420px] max-w-[90vw] bg-surface border-l border-border z-50 flex flex-col shadow-lg"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-divider flex-shrink-0">
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-text-primary truncate">
                  Failed Rows
                </h3>
                <p className="text-xs text-text-secondary truncate">{filename}</p>
              </div>
              <button
                onClick={onClose}
                className="p-1.5 rounded-btn hover:bg-nav-hover text-text-muted hover:text-text-secondary transition-colors"
              >
                <X size={18} />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto">
              {children ? (
                children
              ) : loading ? (
                <div className="p-5 space-y-3 animate-pulse">
                  {[...Array(6)].map((_, i) => (
                    <div key={i} className="h-10 bg-nav-hover rounded-btn" />
                  ))}
                </div>
              ) : (rows || []).length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full py-12 text-text-muted">
                  <p className="text-sm">No failure details available</p>
                </div>
              ) : (
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-surface border-b border-divider">
                    <tr>
                      <th className="text-left px-4 py-2.5 text-text-muted font-semibold uppercase w-14">Row</th>
                      <th className="text-left px-4 py-2.5 text-text-muted font-semibold uppercase w-20">ID No</th>
                      <th className="text-left px-4 py-2.5 text-text-muted font-semibold uppercase w-24">Field</th>
                      <th className="text-left px-4 py-2.5 text-text-muted font-semibold uppercase">Message</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(rows || []).map((r, i) => (
                      <tr
                        key={i}
                        className="border-b border-divider last:border-0 hover:bg-nav-hover transition-colors"
                      >
                        <td className="px-4 py-2 text-text-secondary">{r.row}</td>
                        <td className="px-4 py-2 text-text-primary font-medium">{r.id_no}</td>
                        <td className="px-4 py-2 text-text-secondary">{r.field}</td>
                        <td className="px-4 py-2 text-text-primary">{r.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* Footer */}
            <div className="px-5 py-3 border-t border-divider flex-shrink-0">
              <p className="text-xs text-text-muted">
                {(rows || []).length} failed row{(rows || []).length !== 1 ? "s" : ""} total
              </p>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
