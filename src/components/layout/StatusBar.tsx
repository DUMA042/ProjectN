import { useEffect, useState } from "react";
import { Wifi, WifiOff } from "lucide-react";
import { api } from "@/lib/api";

export default function StatusBar() {
  const [connected, setConnected] = useState(false);
  const [lastRefresh, setLastRefresh] = useState("");

  const checkConnection = async () => {
    try {
      const res = await api.get("/api/health");
      setConnected(res.data?.db === "connected");
    } catch {
      setConnected(false);
    }
    setLastRefresh(new Date().toLocaleTimeString());
  };

  useEffect(() => {
    checkConnection();
    const interval = setInterval(checkConnection, 30_000);
    return () => clearInterval(interval);
  }, []);

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
        <span className="text-text-muted">· flowdb@localhost:5433</span>
      </div>
      <div>
        Last refresh: {lastRefresh || "Never"}
      </div>
    </footer>
  );
}
