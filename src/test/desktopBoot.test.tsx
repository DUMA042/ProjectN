import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import StartupGate from "@/components/layout/StartupGate";
import { apiBaseForPort, resolveApiUrl, setApiBase } from "@/lib/api";
import { DOWNLOAD_ERROR_EVENT } from "@/lib/download";

const tauriMocks = vi.hoisted(() => ({
  isDesktopApp: vi.fn(() => false),
  saveDownload: vi.fn(),
}));

const dialogMocks = vi.hoisted(() => ({
  save: vi.fn(),
}));

vi.mock("@/lib/tauri", () => tauriMocks);
vi.mock("@tauri-apps/plugin-dialog", () => dialogMocks);

import { saveBlob } from "@/lib/download";

beforeEach(() => {
  tauriMocks.isDesktopApp.mockReturnValue(true);
  tauriMocks.saveDownload.mockReset().mockResolvedValue(undefined);
  dialogMocks.save.mockReset().mockResolvedValue("C:\\Users\\HP\\Downloads\\report.csv");
  setApiBase("");
});

describe("runtime api base", () => {
  it("builds the loopback address for the manager port", () => {
    expect(apiBaseForPort(8001)).toBe("http://127.0.0.1:8001");
    expect(apiBaseForPort(8007)).toBe("http://127.0.0.1:8007");
  });

  it("resolves relative api paths against the configured base", () => {
    setApiBase("http://127.0.0.1:8007/");
    expect(resolveApiUrl("/api/reports/x/download")).toBe(
      "http://127.0.0.1:8007/api/reports/x/download"
    );
    expect(resolveApiUrl("api/reports/x/download")).toBe(
      "http://127.0.0.1:8007/api/reports/x/download"
    );
    expect(resolveApiUrl("http://example.test/file")).toBe("http://example.test/file");
    setApiBase("");
    expect(resolveApiUrl("/api/health")).toBe("/api/health");
  });
});

describe("startup gate", () => {
  it("explains the first-run wait", () => {
    render(<StartupGate phase="starting" />);
    expect(screen.getByText("Flow")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Starting the local service");
  });

  it("shows the failure, log location and actions", () => {
    const onRetry = vi.fn();
    const onClose = vi.fn();
    render(
      <StartupGate
        phase="failed"
        message="PostgreSQL did not accept connections."
        onRetry={onRetry}
        onClose={onClose}
      />
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "PostgreSQL did not accept connections."
    );
    expect(screen.getByText(/startup\.log/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onRetry).toHaveBeenCalledOnce();
    expect(onClose).toHaveBeenCalledOnce();
  });
});

function fakeBlob(text: string): Blob {
  return {
    arrayBuffer: async () => new TextEncoder().encode(text).buffer,
  } as unknown as Blob;
}

describe("desktop downloads", () => {
  it("opens the save dialog and writes the file bytes", async () => {
    await saveBlob(fakeBlob("hello"), "report.csv");

    expect(dialogMocks.save).toHaveBeenCalledWith({ defaultPath: "report.csv" });
    expect(tauriMocks.saveDownload).toHaveBeenCalledOnce();
    const [path, bytes] = tauriMocks.saveDownload.mock.calls[0];
    expect(path).toBe("C:\\Users\\HP\\Downloads\\report.csv");
    expect(Array.from(bytes as Uint8Array)).toEqual(
      Array.from(new TextEncoder().encode("hello"))
    );
  });

  it("does nothing when the dialog is cancelled", async () => {
    dialogMocks.save.mockResolvedValue(null);
    await saveBlob(fakeBlob("hello"), "report.csv");
    expect(tauriMocks.saveDownload).not.toHaveBeenCalled();
  });

  it("reports save failures to the app shell", async () => {
    tauriMocks.saveDownload.mockRejectedValue(new Error("disk full"));
    const handler = vi.fn();
    window.addEventListener(DOWNLOAD_ERROR_EVENT, handler);

    await saveBlob(fakeBlob("hello"), "report.csv");

    window.removeEventListener(DOWNLOAD_ERROR_EVENT, handler);
    expect(handler).toHaveBeenCalledOnce();
    expect((handler.mock.calls[0][0] as CustomEvent<string>).detail).toBe("disk full");
  });
});
