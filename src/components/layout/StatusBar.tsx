import { Wifi, WifiOff } from "lucide-react";
import { isHealthy, useHealth } from "@/hooks/useHealth";

export default function StatusBar() {
  const health = useHealth();
  const connected = isHealthy(health.data) && !health.isError;

  return (
    <footer className="h-[32px] flex-shrink-0 bg-surface border-t border-divider px-6 flex items-center justify-between text-xs text-text-muted">
      <div className="flex items-center gap-2">
        {connected ? (
          <>
            <Wifi size={12} className="text-success" />
            <span className="text-success font-medium">Connected</span>
          </>
        ) : (
          <>
            <WifiOff size={12} className="text-danger" />
            <span className="text-danger font-medium">Disconnected</span>
          </>
        )}
        <span className="text-text-muted">· Local attendance database</span>
      </div>
      <div>
        Last check:{" "}
        {health.dataUpdatedAt ? new Date(health.dataUpdatedAt).toLocaleTimeString() : "Never"}
      </div>
    </footer>
  );
}
