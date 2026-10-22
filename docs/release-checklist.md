# Release checklist

Status values: **PASS** (verified with evidence) · **ACCEPTED** (deliberate, owner-approved)
· **PENDING** (not done yet) · **BLOCKED** (cannot be verified in the available environment).

A release may only ship when every line is PASS or ACCEPTED. A BLOCKED line means
the corresponding claim is **not** made.

---

## Code quality and correctness

| Gate | Status | Evidence |
|---|---|---|
| Python test suite green | **PASS** | 253 passed, 0 failed (`pytest tests/`) |
| Frontend unit tests green | **PASS** | 13 passed (`npm test` / vitest) |
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
| D1 Process manager (PG → API → health → window) | **PENDING** | — |
| D1 Single instance + no orphan processes | **PENDING** | — |
| D2 Embedded PostgreSQL first-run init | **PENDING** | — |
| D2 Seeded roster (1,658 employees / 1,423 phones / 40 departments / 8 leave types / 5 rule keys) | **PENDING** | seed tool + dry-run |
| D3 API bundle runs without system Python | **PENDING** | — |
| D4 Deep-path load (HashRouter or SPA fallback) | **PENDING** | — |
| D4 Downloads via Tauri dialog | **PENDING** | — |
| D4 CORS includes Tauri origin; CSP set; capabilities narrowed | **PENDING** | — |
| D5 NSIS per-user installer; uninstall keeps data | **PENDING** | — |
| D6 Clean-Windows install (Sandbox) | **PENDING** | — |
| D6 Upgrade over existing data | **PENDING** | — |
| D6 Operator documentation complete | **PENDING** | — |

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
| Version | 0.1.0 |
| Commit | _filled at release_ |
| Windows build tested | `TBD (D6)` |
| Signed by | _TBD_ |
