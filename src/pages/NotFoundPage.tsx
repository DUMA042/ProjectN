import { Link, useLocation } from "react-router-dom";
import { Compass } from "lucide-react";

/** Unknown route. On desktop this is only reachable through an internal
 * navigation bug, which is exactly when a clear message beats a blank pane. */
export default function NotFoundPage() {
  const location = useLocation();
  return (
    <div className="p-6">
      <div className="card-container p-8 text-center max-w-lg mx-auto">
        <Compass size={32} className="text-text-muted mx-auto mb-3" strokeWidth={1.5} />
        <p className="text-sm font-semibold text-text-primary">Page not found</p>
        <p className="text-xs text-text-secondary mt-1.5">
          This part of the application does not exist. Nothing was lost — your data is unaffected.
        </p>
        <p className="text-[11px] text-text-muted mt-2 break-all">
          Requested: {location.pathname}
        </p>
        <Link
          to="/"
          className="inline-block mt-4 px-4 py-2 text-xs font-medium text-white bg-accent rounded-btn hover:opacity-90 transition-opacity"
        >
          Go to Dashboard
        </Link>
      </div>
    </div>
  );
}
