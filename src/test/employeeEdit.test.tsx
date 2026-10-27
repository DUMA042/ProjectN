import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import EmployeeEditForm from "@/components/ui/EmployeeEditForm";
import EmployeeDetailDrawer from "@/components/ui/EmployeeDetailDrawer";
import { ToastProvider } from "@/components/ui/Toast";
import type { EmployeeDetail, EmployeeLookups } from "@/lib/staff";

const apiMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ api: apiMocks }));

const employee: EmployeeDetail = {
  id_no: "EMP-001",
  full_name: "Ada Lovelace",
  sex: "F",
  department: "Engineering",
  department_id: 1,
  rank: "Officer",
  rank_id: 10,
  grade_level: "GL 08",
  gl_id: 100,
  status: "Active",
  status_id: 3,
  employment_type: "Permanent",
  emp_type_id: 2,
  geographical_zone: "Lagos",
  date_of_last_deployment: "2024-02-29",
  phone_number: "08012345678",
  remark: null,
  card_swipes: [],
  leave_records: [],
  training_records: [],
};

const lookups: EmployeeLookups = {
  departments: [
    { id: 1, name: "Engineering" },
    { id: 2, name: "Finance" },
  ],
  ranks: [
    { id: 10, name: "Officer" },
    { id: 11, name: "Senior Officer" },
  ],
  grade_levels: [
    { id: 100, name: "GL 08" },
    { id: 101, name: "GL 09" },
  ],
  employment_types: [
    { id: 2, name: "Permanent" },
    { id: 3, name: "Contract" },
  ],
  statuses: [
    { id: 3, name: "Active" },
    { id: 4, name: "Leave of Absence" },
  ],
  zones: ["Lagos", "Abuja"],
  sexes: ["F", "M"],
};

function renderForm(onSave = vi.fn(), onCancel = vi.fn()) {
  render(
    <EmployeeEditForm
      employee={employee}
      lookups={lookups}
      saving={false}
      error={null}
      onSave={onSave}
      onCancel={onCancel}
    />
  );
  return { onSave, onCancel };
}

function renderDrawer() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ToastProvider>
        <EmployeeDetailDrawer employeeId={employee.id_no} onClose={() => {}} />
      </ToastProvider>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  apiMocks.get.mockReset();
  apiMocks.post.mockReset();
  apiMocks.patch.mockReset();
});

describe("employee edit form", () => {
  it("shows the employee id as read-only", () => {
    renderForm();
    expect(screen.getByText("EMP-001")).toBeInTheDocument();
    expect(screen.getByText("read-only")).toBeInTheDocument();
  });

  it("sends only the fields that changed", () => {
    const { onSave } = renderForm();
    fireEvent.change(screen.getByLabelText("Full name"), {
      target: { value: "Ada King" },
    });
    fireEvent.change(screen.getByLabelText("Department"), { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

    expect(onSave).toHaveBeenCalledWith({
      full_name: "Ada King",
      department_id: 2,
    });
  });

  it("blocks an invalid phone number", () => {
    const { onSave } = renderForm();
    fireEvent.change(screen.getByLabelText("Phone number"), {
      target: { value: "call me" },
    });
    fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByText(/phone number may contain/i)).toBeInTheDocument();
  });

  it("requires a name", () => {
    const { onSave } = renderForm();
    fireEvent.change(screen.getByLabelText("Full name"), { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByText(/full name is required/i)).toBeInTheDocument();
  });

  it("can clear an optional field", () => {
    const { onSave } = renderForm();
    fireEvent.change(screen.getByLabelText("Phone number"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

    expect(onSave).toHaveBeenCalledWith({ phone_number: null });
  });
});

describe("employee detail drawer editing", () => {
  it("opens the editor from the pencil button", async () => {
    apiMocks.get.mockImplementation((url: string) => {
      if (url.includes("/detail")) return Promise.resolve({ data: employee });
      if (url.includes("attendance-stats")) {
        return Promise.resolve({
          data: { summary: {}, avg_work_hours: null, daily_attendance: [] },
        });
      }
      if (url.includes("/lookups")) return Promise.resolve({ data: lookups });
      return Promise.resolve({ data: {} });
    });
    apiMocks.post.mockResolvedValue({ data: { groups: [] } });

    renderDrawer();

    const pencil = await screen.findByRole("button", { name: /edit employee/i });
    fireEvent.click(pencil);

    await waitFor(() => {
      expect(screen.getByLabelText("Full name")).toHaveValue("Ada Lovelace");
    });
    expect(apiMocks.get).toHaveBeenCalledWith("/api/employees/lookups");
    expect(screen.queryByText(/avg work hours/i)).not.toBeInTheDocument();
  });
});
