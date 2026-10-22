import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import App from "@/App";
import { resolveApiBase } from "@/lib/api";
import { saveUrl } from "@/lib/download";
import { ServiceBannerView } from "@/components/layout/ServiceBanner";
import { safeLocalStorage } from "@/hooks/useManagementScope";

function renderAt(route: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[route]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("api base resolution", () => {
  it("uses an explicit setting and strips trailing slashes", () => {
    expect(resolveApiBase("https://api.example/api/", false)).toBe("https://api.example/api");
  });

  it("uses the dev proxy (same origin) in development", () => {
    expect(resolveApiBase(undefined, true)).toBe("");
    expect(resolveApiBase("   ", true)).toBe("");
  });

  it("targets the local service outside development (desktop build)", () => {
    expect(resolveApiBase(undefined, false)).toBe("http://127.0.0.1:8001");
  });
});

describe("routing safety", () => {
  it("renders the 404 card for an unknown route", () => {
    renderAt("/does-not-exist");
    expect(screen.getByText("Page not found")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Go to Dashboard" })).toBeInTheDocument();
  });

  it("keeps the shell (sidebar) visible", () => {
    renderAt("/");
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });
});

describe("service banner", () => {
  it("is hidden while the service is reachable", () => {
    const { container } = render(<ServiceBannerView offline={false} onRetry={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("explains the failure and offers retry", () => {
    const onRetry = vi.fn();
    render(<ServiceBannerView offline onRetry={onRetry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Cannot reach the local service");
    screen.getByRole("button", { name: /retry/i }).click();
    expect(onRetry).toHaveBeenCalledOnce();
  });
});

describe("safe storage", () => {
  it("returns null for corrupt JSON instead of throwing", () => {
    window.localStorage.setItem("corrupt", "{not json");
    expect(safeLocalStorage.getItem("corrupt")).toBeNull();
    window.localStorage.removeItem("corrupt");
  });

  it("returns valid payloads unchanged", () => {
    const payload = JSON.stringify({ state: { tab: "pulse" }, version: 2 });
    window.localStorage.setItem("ok", payload);
    expect(safeLocalStorage.getItem("ok")).toBe(payload);
    window.localStorage.removeItem("ok");
  });

  it("never throws when storage itself fails", () => {
    const spy = vi.spyOn(window.localStorage, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(safeLocalStorage.getItem("x")).toBeNull();
    spy.mockRestore();
  });
});

describe("download helper", () => {
  it("triggers an anchor with the requested filename", () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    saveUrl("/api/reports/build/x/download", "HR_Report.docx");
    expect(click).toHaveBeenCalledOnce();
    const anchor = click.mock.instances[0] as unknown as HTMLAnchorElement;
    expect(anchor.download).toBe("HR_Report.docx");
    expect(anchor.getAttribute("href")).toBe("/api/reports/build/x/download");
    click.mockRestore();
  });
});
