# Known limitations (release 0.1.0)

This file records what the application **does not** do, and the consequences.
Items marked *accepted* are deliberate decisions, not oversights.

## 1. No authentication or authorisation — **accepted**

- The API listens on `127.0.0.1` only and there is no login, token, or role model.
- Any process or user account on the same machine can read staff data, trigger
  report generation, delete reports, resolve anonymised tokens
  (`POST /api/privacy/unhash`), or change attendance rules.
- Mitigations in place: loopback binding, OS user accounts, single-instance guard.
- Consequence: Flow assumes a trusted, single-user Windows machine.
- Roster edits (Management → People → Directory → pencil) follow the same model:
  anyone at the machine can change a staff member's name, sex, phone number,
  status, department, rank, grade level, employment type, zone, or last
  deployment date.

## 2. No backup or restore — **accepted**

- There is no backup button, no scheduled copy, and no documented recovery
  procedure (deliberately out of scope for this release).
- Consequences:
  - Disk failure, theft, or a Windows reinstall **destroys all data permanently**.
  - Losing the `privacy_tokens` table makes every hashed report in
    `report_inbox` permanently unreadable — the mapping cannot be reconstructed.
  - An uninstall keeps `%APPDATA%\Flow`; deleting that folder deletes everything.
- `pg_dump`/`pg_restore` exist on the machine but are unsupported by the product.

## 3. No audit trail — **accepted (blocked by item 1)**

- Ingestion, deletions, token resolution, reprocessing and rule changes are not
  attributed to a person.
- Consequence: "who deleted this report / changed these rules" cannot be
  answered. The AI layer keeps a field-access audit, but nothing for user actions.
- Manual roster edits are not attributed either. They do close department,
  rank, and grade-level tenure rows exactly like a nominal-roll upload, but the
  edit itself leaves no record of who made it or what changed.

## 4. Performance is unverified — **accepted**

- No measurements were taken by decision. Startup time, import time, dashboard
  latency and report generation time on target hardware are **unknown**.
- Consequence: no performance claim can be made; slow behaviour on low-spec
  machines is untested.

## 5. Personal data ships inside the installer — **accepted**

- The installer seeds employee master data: names, employee IDs, sex, employment
  status, and **phone numbers** (1,423 of 1,658 staff have one).
- Consequences:
  - Anyone holding the installer holds that data.
  - Uninstalling does not remove `%APPDATA%\Flow`, so seeded data persists.
  - `full_name`, `id_no`, `phone_number`, `sex` and employment status are treated
    as sensitive by the AI layer.

## 6. Single instance, default-first ports

- Only one Flow instance may run per Windows account (a second launch focuses the
  existing window). Two instances must never share one PostgreSQL data directory.
- The API starts at **8001** and PostgreSQL at **5433**, walking upward if a port
  is occupied. Chosen ports are written to
  `%APPDATA%\Flow\logs\startup.log`.
- Consequence: two Windows users cannot run Flow simultaneously on one PC, and
  support must read the log to know the port in use.

## 7. Seeded roster is a snapshot

- Employee data is captured at packaging time. New hires, transfers, and
  departures are not reflected until a nominal roll is uploaded again.
- 235 employees currently have no phone number in the source data; the seed
  preserves that gap.
- Uploads of swipe/leave/training files are refused while the roster is empty.

## 8. Read-only database role not created

- The `flow_reader` role described in `scripts/add_readonly_role.sql` does not
  exist. AI queries run in the application session inside a read-only
  transaction with a 15 s statement timeout and a 2,000-row cap.

## 9. Testing and tooling gaps

- No frontend end-to-end tests; component-level vitest coverage only.
- Database-dependent tests use the local PostgreSQL; some use SQLite, which can
  hide PostgreSQL-specific behaviour.
- `attendance_daily` is created outside the ORM and excluded from autogenerate;
  schema changes to it must be written by hand.
- The installer is unsigned: Windows SmartScreen may warn on first run.
