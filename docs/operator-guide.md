# Flow operator guide (version 0.1.1)

Flow runs entirely on this PC. It includes its own database and application
server; nothing else needs to be installed, and no data leaves the machine
except optional AI requests when a DeepSeek key is configured.

## Requirements

- Windows 10 or 11, 64-bit.
- About 400 MB of free disk space.
- No administrator rights are needed or wanted.

## Installing

1. Run `Flow_0.1.1_x64-setup.exe`.
2. The installer places the program in `%LOCALAPPDATA%\Flow` for the current
   user and creates a Start Menu entry. It does not require elevation.
3. Windows SmartScreen may warn because the installer is not code-signed.
   The installer is the file supplied with the release; verify its SHA-256 if
   you received it through another channel.

## First run

Double-click **Flow** in the Start Menu. A startup screen appears while Flow
prepares its private database and loads the staff roster. This can take up to
about a minute the first time and is usually much faster afterwards. When the
window opens, the dashboard is ready.

If the startup screen shows an error instead, see Troubleshooting below. The
error text and the log location are displayed on that screen.

## Daily use

- Launch Flow from the Start Menu. Only one copy can run; launching again
  brings the existing window forward.
- Data is saved automatically. Close the window when finished; Flow stops its
  background services cleanly.
- **Do not run Flow as administrator.** PostgreSQL refuses to run with
  elevated rights, and the startup screen will report an error.

## Where things are stored

| Item | Location |
|---|---|
| Program and bundled services | `%LOCALAPPDATA%\Flow` |
| Database, uploads, reports | `%APPDATA%\Flow\data` and `%APPDATA%\Flow\pgdata` |
| Logs | `%APPDATA%\Flow\logs` (`startup.log`, `api.log`, `postgres.log`) |

Uninstalling removes the program but **keeps `%APPDATA%\Flow`**. That folder is
your data. Removing it deletes everything permanently.

Flow prefers ports 8001 (application service) and 5433 (database) and walks
upward if they are taken. The ports actually used are written to
`%APPDATA%\Flow\logs\startup.log` on each launch.

## Optional: enabling AI features

AI features are disabled until a DeepSeek key is provided.

1. Open Windows Settings, search for "environment variables", and add a user
   variable named `DEEPSEEK_API_KEY` with your key as the value.
2. Optionally set `DEEPSEEK_MODEL` (defaults to the configured model).
3. Close and reopen Flow.

The key is read by the local service only; it is never written to the database
or returned to the interface. Never share the key or commit it to a file in the
program folder.

## Upgrading

Run the newer installer over the existing installation. The program files are
replaced; the database, settings and reports in `%APPDATA%\Flow` are kept and
migrations run automatically on the next launch.

## Uninstalling

Use Windows Settings → Apps → Flow, or `uninstall.exe` in the install folder.
The program is removed. `%APPDATA%\Flow` remains so a reinstall keeps your data.
To remove everything, delete `%APPDATA%\Flow` afterwards; this cannot be undone.

## Backups

Flow has no built-in backup or restore. If you need a copy, close Flow and copy
the whole `%APPDATA%\Flow` folder to another drive. Restoring is the reverse:
close Flow, restore the folder, then start Flow.

## Troubleshooting

| Symptom | What to do |
|---|---|
| Startup screen: "PostgreSQL did not become ready" | Close other copies of Flow; check free disk space; check antivirus is not blocking `%LOCALAPPDATA%\Flow\postgres`; retry. |
| Startup screen: "Flow could not start" with another message | Read `%APPDATA%\Flow\logs\startup.log`; the last lines name the failing step. |
| Window opens but shows "Cannot reach the local service" | Wait a few seconds and press Retry. If it persists, close and reopen Flow, then check `api.log`. |
| Everything worked yesterday, now fails immediately | The PC may have restarted mid-run; PostgreSQL recovers automatically on the next launch. If not, check `postgres.log`. |
| SmartScreen blocks the installer | Choose "More info" → "Run anyway" only if the file came from the expected release. |
| Need to know which ports are in use | Open `%APPDATA%\Flow\logs\startup.log` and read the `starting:` line. |

When contacting support, send the three files in `%APPDATA%\Flow\logs`. They do
not contain staff records, but review them before sharing outside your
organisation.
