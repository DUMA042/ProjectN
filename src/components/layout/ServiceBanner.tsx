import { RefreshCw, ServerCrash } from "lucide-react";
import { isHealthy, useHealth } from "@/hooks/useHealth";

/** Presentational half — rendered in tests without a network. */
export function ServiceBannerView({
  offline,
  onRetry,
}: {
  offline: boolean;
  onRetry: () => void;
}) {
  if (!offline) return null;
  return (
    <div
      role="alert"
      className="flex-shrink-0 border-b border-badge-red-bg bg-badge-red-bg px-6 py-2 flex items-center gap-2 text-xs text-danger"
    >
      <ServerCrash size={14} className="flex-shrink-0" />
      <span className="font-medium">Cannot reach the local service.</span>
      <span className="text-text-secondary">
        The application server may not have started yet. Your data is safe.
      </span>
      <button
        onClick={onRetry}
        className="ml-auto inline-flex items-center gap-1 px-2.5 py-1 rounded-btn border border-danger/40 hover:bg-surface transition-colors"
      >
        <RefreshCw size={12} /> Retry
      </button>
    </div>
  );
}

/** Container: polls health and shows the banner while the API is unreachable. */
export default function ServiceBanner() {
  const health = useHealth();
  // Only claim "offline" once the request has actually failed — avoid a flash
  // of red during the very first render.
  const offline = health.isError || (health.isFetched && !isHealthy(health.data));
  return (
    <ServiceBannerView
      offline={offline}
      onRetry={() => {
        void health.refetch();
      }}
    />
  );
}
