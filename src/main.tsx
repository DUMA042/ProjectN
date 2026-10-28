import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import { HashRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import StartupGate from "@/components/layout/StartupGate";
import { apiBaseForPort, setApiBase } from "@/lib/api";
import {
  closeWindow,
  getBackendStatus,
  isDesktopApp,
  type BackendStatus,
} from "@/lib/tauri";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
});

const STARTUP_TIMEOUT_MS = 120_000;
const POLL_INTERVAL_MS = 500;

/**
 * In a packaged desktop run the API port is chosen at startup, so the window
 * waits for the host to report it. Browser builds render immediately.
 */
function Root() {
  const desktop = isDesktopApp();
  const [status, setStatus] = useState<BackendStatus>(
    desktop ? { state: "starting" } : { state: "disabled" }
  );

  useEffect(() => {
    if (!desktop) return;
    let cancelled = false;
    const startedAt = Date.now();

    const poll = async () => {
      if (cancelled) return;
      try {
        const next = await getBackendStatus();
        if (cancelled) return;

        if (next.state === "ready") {
          setApiBase(apiBaseForPort(next.api_port));
        }
        if (next.state === "ready" || next.state === "failed" || next.state === "disabled") {
          setStatus(next);
          return;
        }
        if (Date.now() - startedAt >= STARTUP_TIMEOUT_MS) {
          setStatus({
            state: "failed",
            message: "The local service did not become ready in time.",
          });
          return;
        }
        window.setTimeout(poll, POLL_INTERVAL_MS);
      } catch {
        if (cancelled) return;
        if (Date.now() - startedAt >= STARTUP_TIMEOUT_MS) {
          setStatus({
            state: "failed",
            message: "Could not reach the local service.",
          });
          return;
        }
        window.setTimeout(poll, POLL_INTERVAL_MS * 2);
      }
    };

    void poll();
    return () => {
      cancelled = true;
    };
  }, [desktop]);

  if (status.state === "starting") {
    return <StartupGate phase="starting" />;
  }

  if (status.state === "failed") {
    return (
      <StartupGate
        phase="failed"
        message={status.message}
        onRetry={() => window.location.reload()}
        onClose={() => {
          void closeWindow();
        }}
      />
    );
  }

  return (
    <HashRouter>
      <App />
    </HashRouter>
  );
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <Root />
    </QueryClientProvider>
  </React.StrictMode>
);
