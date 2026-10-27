import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import FileFormatGuide from "@/components/upload/FileFormatGuide";
import FileDropZone from "@/components/ui/FileDropZone";
import type { FileFormatsResponse } from "@/lib/fileSchema";

const apiMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ api: apiMocks }));

const payload: FileFormatsResponse = {
  filename_pattern: "DEPT_TYPE_YYYYMM_vN.xlsx",
  note: "Only .xlsx files are accepted.",
  types: [
    {
      id: "nominal",
      label: "Nominal Roll",
      accepted: ".xlsx",
      header_rows: 1,
      data_starts_row: 2,
      min_columns: 29,
      positional: true,
      detection: "headers",
      filename_example: "AHRD_Nominal_202610_v1.xlsx",
      required_indexes: [1, 3],
      columns: [
        { index: 0, header: "S/N", usage: "ignored" },
        { index: 1, header: "Name", usage: "required" },
        { index: 3, header: "ID No.", usage: "required" },
      ],
      warnings: ["Columns are read by position."],
    },
    {
      id: "leave",
      label: "Leave",
      accepted: ".xlsx",
      header_rows: 2,
      data_starts_row: 3,
      min_columns: 38,
      positional: true,
      detection: "two headers",
      filename_example: "AHRD_Leave_202610_v1.xlsx",
      required_indexes: [2],
      columns: [
        { index: 2, header: "STAFF ID", usage: "required" },
        { index: 3, header: "GL", usage: "ignored" },
      ],
      warnings: ["Leave files use two header rows."],
    },
  ],
};

function renderGuide() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <FileFormatGuide open onClose={() => {}} />
    </QueryClientProvider>
  );
}

beforeEach(() => {
  apiMocks.get.mockReset();
  apiMocks.get.mockResolvedValue({ data: payload });
});

describe("file format guide", () => {
  it("lists the report types and the required columns of the first tab", async () => {
    renderGuide();

    expect(await screen.findByRole("tab", { name: "Nominal Roll" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Leave" })).toBeInTheDocument();

    await waitFor(() => expect(screen.getByText("ID No.")).toBeInTheDocument());
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText(/row 1 is the column header/i)).toBeInTheDocument();
    expect(screen.queryByText("S/N")).not.toBeInTheDocument();
  });

  it("reveals unused columns on request", async () => {
    renderGuide();
    await waitFor(() => expect(screen.getByText("ID No.")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /show unused columns/i }));
    expect(screen.getByText("S/N")).toBeInTheDocument();
  });

  it("explains the two header rows for leave files", async () => {
    renderGuide();
    await waitFor(() => expect(screen.getByText("ID No.")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("tab", { name: "Leave" }));
    expect(screen.getByText(/rows 1 and 2 are headers/i)).toBeInTheDocument();
    expect(screen.getByText("STAFF ID")).toBeInTheDocument();
    expect(screen.getByText(/leave files use two header rows/i)).toBeInTheDocument();
  });
});

describe("upload drop zone format link", () => {
  it("calls the help handler without opening the file picker", () => {
    const onShowFormatHelp = vi.fn();
    render(
      <FileDropZone
        files={[]}
        onFilesAdded={() => {}}
        onRemoveFile={() => {}}
        onClearAll={() => {}}
        onShowFormatHelp={onShowFormatHelp}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /what format does my file need/i }));
    expect(onShowFormatHelp).toHaveBeenCalledTimes(1);
  });

  it("renders no extra link when no handler is provided", () => {
    render(
      <FileDropZone
        files={[]}
        onFilesAdded={() => {}}
        onRemoveFile={() => {}}
        onClearAll={() => {}}
      />
    );
    expect(
      screen.queryByRole("button", { name: /what format does my file need/i })
    ).not.toBeInTheDocument();
  });
});
