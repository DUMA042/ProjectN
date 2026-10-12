import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import App from "@/App";

function shell(route = "/") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  window.history.pushState({}, "", route);
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[route]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("app shell", () => {
  it("renders the sidebar nav", () => {
    shell("/");
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Report Builder")).toBeInTheDocument();
    expect(screen.getByText("Individual Report")).toBeInTheDocument();
  });

  it("renders the report builder route", () => {
    shell("/reports");
    expect(screen.getByRole("heading", { name: "Report Builder" })).toBeInTheDocument();
  });
});
