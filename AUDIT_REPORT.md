# Initial source audit — 2026-10-10

Authoritative root: `DR`, branded QueueLess Pulse, with separate models/config and customer/staff/public templates. `QueueLess_MVP` is the earlier monolithic starter; preserved untouched. Timestamps are too close to establish provenance alone; structure and branding establish the target.

Initial compilation of app.py, models.py, config.py passed on bundled Python 3.12.14. No syntax defect was reproduced. Global python points to a Windows Store alias; py is absent. Bundled Python is usable. Initial venv ensurepip failed because sandbox TEMP was unwritable; redirecting TEMP/TMP inside workspace succeeded.

Source findings (before fixes):

| Severity | Defect | Impact |
| --- | --- | --- |
| Critical | Default secret and admin/admin123 provisioning | Forged sessions / trivial staff access |
| High | Latest-ticket locking without daily unique constraint | Duplicate numbering, especially empty queues |
| High | Call Next implicitly completes active token and uses SKIP LOCKED | Double call / FIFO violation / false audit history |
| High | Complete and skip read without shared serialization | Conflicting state updates and duplicate events |
| High | No CSRF; logout via GET | Cross-site staff mutations |
| High | Production SQLite fallback | Ephemeral data loss / wrong database |
| High | Tests change database URI after db.init_app | Tests can target the existing development database |
| Medium | Daily-number ordering across historical dates | New-day tokens overtake previous-day waiters |
| Medium | ETA omits active customer; terminal states retain ahead count | Misleading tracking |
| Medium | Public service name interpolated into innerHTML | Stored script injection if names are compromised |
| Medium | Worker scope only /static; icons absent | Incomplete PWA |
| Medium | Silent exceptions in call route | Failure appears successful |
| Medium | TESTING_REPORT claims three passes with no evidence | Unreliable engineering evidence |

Customer selection, issue, tracking, staff login/dashboard/actions and display routes exist; execution evidence is recorded separately after testing. Cancellation, health checks, safe duplicate submissions, migrations and PostgreSQL/browser tests were absent. QR entry, throughput analytics and live announcements claimed in README are not implemented in this root.
