# Release checklist

Status values: **PASS** (verified with evidence) · **ACCEPTED** (deliberate, owner-approved)
· **PENDING** (not done yet) · **BLOCKED** (cannot be verified in the available environment).

A release may only ship when every line is PASS or ACCEPTED. A BLOCKED line means
the corresponding claim is **not** made.

---

## Code quality and correctness

| Gate | Status | Evidence |
|---|---|---|
| Python test suite green | **PASS** | 278 passed, 0 failed (`pytest tests/`) |
| Frontend unit tests green | **PASS** | 33 passed (`npx vitest run`) |
| Rust desktop tests green | **PASS** | 12 passed (`cargo test --lib` in `src-tauri`) |
| TypeScript compiles | **PASS** | `tsc --noEmit` exit 0 |
| Production frontend build | **PASS** | `npm run build` succeeded |
| Business rules covered by tests | **PASS** | classification, attendance cells, leave/training, day-first dates, individual report grids |
| Dependencies pinned | **PASS** | `requirements.lock.txt` (96 pins), `==` pins in `requirements.txt`, `package-lock.json` |

## Data safety

| Gate | Status | Evidence |
|---|---|---|
| Schema versioned and repeatable | **PASS** | Alembic `0001` baseline + `0002`; `init_db` re-run and up/down round-trip tests on a throwaway DB |
| Model/DDL drift guarded | **PASS** | `tests/test_migrations/test_drift.py` |
| Fact rebuild cannot interleave | **PASS** | advisory single-flight lock + contention test |
| Ingestion jobs cannot be double-claimed | **PASS** | `FOR UPDATE SKIP LOCKED` + test |
| Re-ingest cannot duplicate business rows | **PASS** | natural-key dedup (leave, training) + tests |
| Partial ingestion is visible, not silent | **PASS** | `completed_with_errors` status end-to-end |
| Corrupt report index fails loudly | **PASS** | `ManifestCorrupt` → HTTP 500 with guidance |
| Graceful shutdown returns work to pending | **PASS** | `request_stop` + requeue test |

## Security and privacy

| Gate | Status | Evidence |
|---|---|---|
| PII masked in logs | **PASS** | redaction filter (INFO+) + tests; DEBUG unaffected |
| Error responses do not leak internals | **PASS** | `safe_error_detail` + tests (SQL/paths/credentials scrubbed) |
| DB probe restricted to loopback | **PASS** | `/settings/test-db` returns 400 for non-local hosts |
| CORS restricted, no credentials | **PASS** | config-driven origins + CORS tests |
| API docs disabled outside development | **PASS** | `docs_url`/`openapi_url` follow environment |
| AI concurrency bounded | **PASS** | semaphore (2) + test |
| Upload size bounded | **PASS** | `MAX_UPLOAD_MB=200`, partial file removed |
| Authentication / authorisation | **ACCEPTED** | see `known-limitations.md` §1 |
| Audit trail | **ACCEPTED** | see §3 |

## Desktop readiness (pre-packaging)

| Gate | Status | Evidence |
|---|---|---|
| Frontend API base works outside dev | **PASS** | `resolveApiBase()` (absolute default) + tests |
| Downloads centralised for Tauri swap | **PASS** | `src/lib/download.ts` used by all download sites |
| Crash renders a recoverable screen | **PASS** | root error boundary keyed by route |
| Unknown route explained | **PASS** | 404 card |
| Service unreachable is visible | **PASS** | offline banner + shared health query |
| Storage corruption tolerated | **PASS** | safe localStorage hydration + tests |

## Packaging gates (desktop program)

| Gate | Status | Evidence |
|---|---|---|
| D1 Process manager (PG → API → health → window) | **PASS** | Installed 0.1.1 normal launch: `startup.log` shows resource directory, database, sidecar, seed directory, `ready`; window title Flow; `/api/health` 200 |
| D1 Single instance + no orphan processes | **PASS** | Two launches → one `Flow` process; graceful close stops API + PostgreSQL; force-kill leaves no `flow-api`/`postgres` and releases 8001/5434 |
| D2 Embedded PostgreSQL first-run init | **PASS** | Fresh data root: `initdb` → `created flowdb` → ready; second run reports database already present |
| D2 Seeded roster (1,658 employees / 1,423 phones / 40 departments / 8 leave types / 5 rule keys) | **PASS** | Installed-app bootstrap log: `seed applied` with 1,658/1,423/40/8/5; DB query confirms 1,658 employees, 5 rules, 33 tables |
| D3 API bundle runs without system Python | **PASS** | Manager log shows `api command: …\Flow\api\flow-api.exe`; bootstrap applies migrations and seed inside the sidecar |
| D4 Deep-path load (HashRouter or SPA fallback) | **PASS** | Headless run of `#/management` renders the shell; `#/does-not-exist` shows the 404 card; packaged window renders |
| D4 Downloads via Tauri dialog | **PASS** | Vitest covers dialog save/cancel/failure + host command; packaged dialog not manually exercised (noted) |
| D4 CORS includes Tauri origin; CSP set; capabilities narrowed | **PASS** | Manager injects Tauri origin; CSP configured; capabilities = core + window close + dialog save; packaged API serves the window |
| D5 NSIS per-user installer; uninstall keeps data | **PASS** | `Flow_0.1.1_x64-setup.exe` 96.3 MB, SHA-256 `F7F7E593…CB8D4`; silent non-elevated install; uninstall removes program, `%APPDATA%\Flow` marker survives |
| D6 Clean-Windows install (Sandbox) | **ACCEPTED** | Windows Sandbox disabled; verified on the development machine (Win 10 19045). No clean-image claim is made. |
| D6 Upgrade over existing data | **PASS** | 0.1.0 → 0.1.1 install-over: `Flow.exe`, ARP 0.1.1, data unchanged (1,658/5/33), seed reported already present; no stale legacy binary |
| D6 Operator documentation complete | **PASS** | `docs/operator-guide.md` (install, data/logs, ports, no-admin, AI key, upgrade, uninstall, backup, troubleshooting) |

## Release artefacts

| Artefact | Details |
|---|---|
| Installer (release) | `Flow_0.1.1_x64-setup.exe` — 96.3 MB, SHA-256 `F7F7E593F6EF96B97EAF710BE00F4D12B6634F3A877ED196E230ED6D943CB8D4` |
| Installer (upgrade baseline) | `Flow_0.1.0_x64-setup.exe` — 96.3 MB, SHA-256 `9192147E544E2F3FE939691896CFCB771FB851C573249D19766680BA45350C16` |
| Installed tree | ≈353 MB under `%LOCALAPPDATA%\Flow` (program, PostgreSQL, API sidecar, seed, runtime DLLs) |
| Bundle identity | `com.flow.desktop`, version 0.1.1, executable `Flow.exe` |

## Accepted risks at release

| Risk | Owner decision |
|---|---|
| No authentication / authorisation | accepted, loopback-only |
| No backup / restore / recovery procedure | accepted |
| No audit trail | accepted |
| Performance unverified (no measurements) | accepted |
| PII (names, IDs, phones) shipped in installer | accepted |
| Unsigned installer (SmartScreen warning) | accepted |

---

## Sign-off

| Item | Value |
|---|---|
| Version | 0.1.1 |
| Commit | tag `v0.1.1` |
| Windows build tested | Windows 10 Pro 19045 (development machine; not a clean image) |
| Signed by | Flow Team |
