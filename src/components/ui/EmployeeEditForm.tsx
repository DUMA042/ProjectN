import { useState, type FormEvent } from "react";
import { Lock, Loader2 } from "lucide-react";
import type {
  EmployeeDetail,
  EmployeeLookups,
  LookupOption,
  EmployeeUpdatePayload,
} from "@/lib/staff";

interface EmployeeEditFormProps {
  employee: EmployeeDetail;
  lookups: EmployeeLookups;
  saving: boolean;
  error: string | null;
  onSave: (changes: EmployeeUpdatePayload) => void;
  onCancel: () => void;
}

const FIELD =
  "w-full px-2 py-1.5 border border-border rounded-input bg-surface text-text-primary text-sm";
const LABEL = "text-xs text-text-muted";

const PHONE_RE = /^[0-9+()\-\s]{3,30}$/;

function toNumber(value: string): number | null {
  if (!value) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

/** Include the current value even if a lookup list no longer contains it. */
function withCurrent(options: LookupOption[], currentId: number | null): LookupOption[] {
  if (currentId == null || options.some((o) => o.id === currentId)) return options;
  return [{ id: currentId, name: `#${currentId}` }, ...options];
}

export default function EmployeeEditForm({
  employee,
  lookups,
  saving,
  error,
  onSave,
  onCancel,
}: EmployeeEditFormProps) {
  const [fullName, setFullName] = useState(employee.full_name);
  const [sex, setSex] = useState(employee.sex ?? "");
  const [phone, setPhone] = useState(employee.phone_number ?? "");
  const [zone, setZone] = useState(employee.geographical_zone ?? "");
  const [deployment, setDeployment] = useState(employee.date_of_last_deployment ?? "");
  const [departmentId, setDepartmentId] = useState(
    employee.department_id == null ? "" : String(employee.department_id)
  );
  const [rankId, setRankId] = useState(
    employee.rank_id == null ? "" : String(employee.rank_id)
  );
  const [glId, setGlId] = useState(employee.gl_id == null ? "" : String(employee.gl_id));
  const [empTypeId, setEmpTypeId] = useState(
    employee.emp_type_id == null ? "" : String(employee.emp_type_id)
  );
  const [statusId, setStatusId] = useState(
    employee.status_id == null ? "" : String(employee.status_id)
  );
  const [localError, setLocalError] = useState<string | null>(null);

  const submit = (event: FormEvent) => {
    event.preventDefault();

    const name = fullName.trim();
    if (!name) {
      setLocalError("Full name is required.");
      return;
    }
    const phoneValue = phone.trim() || null;
    if (phoneValue && !PHONE_RE.test(phoneValue)) {
      setLocalError("Phone number may contain digits, spaces, +, -, ( ) only.");
      return;
    }

    const payload: EmployeeUpdatePayload = {};
    if (name !== employee.full_name) payload.full_name = name;
    if ((sex || null) !== (employee.sex ?? null)) payload.sex = sex || null;
    if (phoneValue !== (employee.phone_number ?? null)) payload.phone_number = phoneValue;
    if ((zone.trim() || null) !== (employee.geographical_zone ?? null)) {
      payload.geographical_zone = zone.trim() || null;
    }
    if ((deployment || null) !== (employee.date_of_last_deployment ?? null)) {
      payload.date_of_last_deployment = deployment || null;
    }
    const numeric: [keyof EmployeeUpdatePayload, string, number | null][] = [
      ["department_id", departmentId, employee.department_id],
      ["rank_id", rankId, employee.rank_id],
      ["gl_id", glId, employee.gl_id],
      ["emp_type_id", empTypeId, employee.emp_type_id],
      ["status_id", statusId, employee.status_id],
    ];
    for (const [field, raw, original] of numeric) {
      const next = toNumber(raw);
      if (next !== (original ?? null)) {
        (payload as Record<string, number | null>)[field] = next;
      }
    }

    setLocalError(null);
    if (Object.keys(payload).length === 0) {
      onCancel();
      return;
    }
    onSave(payload);
  };

  const message = localError || error;

  return (
    <form onSubmit={submit} className="space-y-4">
      {message && (
        <p className="text-xs text-danger bg-danger/10 border border-danger/30 rounded-input px-3 py-2">
          {message}
        </p>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div className="col-span-2">
          <label className={LABEL} htmlFor="edit-full-name">
            Full name
          </label>
          <input
            id="edit-full-name"
            className={FIELD}
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            autoFocus
          />
        </div>

        <div className="col-span-2">
          <span className={LABEL}>Employee ID</span>
          <div className="flex items-center gap-1.5 px-2 py-1.5 border border-border rounded-input bg-nav-hover text-text-muted text-sm">
            <Lock size={12} />
            <span className="font-mono">{employee.id_no}</span>
            <span className="ml-auto text-[10px]">read-only</span>
          </div>
        </div>

        <div>
          <label className={LABEL} htmlFor="edit-department">
            Department
          </label>
          <select
            id="edit-department"
            className={FIELD}
            value={departmentId}
            onChange={(e) => setDepartmentId(e.target.value)}
          >
            <option value="">—</option>
            {withCurrent(lookups.departments, employee.department_id).map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className={LABEL} htmlFor="edit-rank">
            Rank
          </label>
          <select
            id="edit-rank"
            className={FIELD}
            value={rankId}
            onChange={(e) => setRankId(e.target.value)}
          >
            <option value="">—</option>
            {withCurrent(lookups.ranks, employee.rank_id).map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className={LABEL} htmlFor="edit-grade-level">
            Grade level
          </label>
          <select
            id="edit-grade-level"
            className={FIELD}
            value={glId}
            onChange={(e) => setGlId(e.target.value)}
          >
            <option value="">—</option>
            {withCurrent(lookups.grade_levels, employee.gl_id).map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className={LABEL} htmlFor="edit-employment-type">
            Employment type
          </label>
          <select
            id="edit-employment-type"
            className={FIELD}
            value={empTypeId}
            onChange={(e) => setEmpTypeId(e.target.value)}
          >
            <option value="">—</option>
            {withCurrent(lookups.employment_types, employee.emp_type_id).map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className={LABEL} htmlFor="edit-status">
            Status
          </label>
          <select
            id="edit-status"
            className={FIELD}
            value={statusId}
            onChange={(e) => setStatusId(e.target.value)}
          >
            <option value="">—</option>
            {withCurrent(lookups.statuses, employee.status_id).map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className={LABEL} htmlFor="edit-sex">
            Sex
          </label>
          <select
            id="edit-sex"
            className={FIELD}
            value={sex}
            onChange={(e) => setSex(e.target.value)}
          >
            <option value="">—</option>
            {lookups.sexes.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className={LABEL} htmlFor="edit-zone">
            Geo zone
          </label>
          <input
            id="edit-zone"
            list="employee-zone-options"
            className={FIELD}
            value={zone}
            onChange={(e) => setZone(e.target.value)}
          />
          <datalist id="employee-zone-options">
            {lookups.zones.map((value) => (
              <option key={value} value={value} />
            ))}
          </datalist>
        </div>

        <div>
          <label className={LABEL} htmlFor="edit-phone">
            Phone number
          </label>
          <input
            id="edit-phone"
            className={FIELD}
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="0801 234 5678"
          />
        </div>

        <div>
          <label className={LABEL} htmlFor="edit-deployment">
            Last deployment
          </label>
          <input
            id="edit-deployment"
            type="date"
            className={FIELD}
            value={deployment}
            onChange={(e) => setDeployment(e.target.value)}
          />
        </div>
      </div>

      <div className="flex items-center justify-end gap-2 pt-1">
        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          className="px-3 py-1.5 text-sm rounded-btn border border-border text-text-secondary hover:bg-nav-hover"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={saving}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-btn bg-accent text-white hover:opacity-90 disabled:opacity-60"
        >
          {saving && <Loader2 size={14} className="animate-spin" />}
          Save changes
        </button>
      </div>
    </form>
  );
}
