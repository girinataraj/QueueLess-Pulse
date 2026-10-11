# Erode Eye Clinic — DEMO: integrated localhost handoff

This fictional clinic uses synthetic tickets only. No real hospital affiliation is claimed. The integrated candidate is in `C:\Users\girin\.codex\worktrees\erode-monday-integration\DR`, separate from the verified fallback and Antigravity's original worktree. No GitHub main, Render or hosted database changes are part of this release.

## Open the candidate

| Experience | URL |
| --- | --- |
| Reception sign in | http://127.0.0.1:5001/app/staff/login?experience=reception |
| Reception dashboard: QR, download, print and live counts | http://127.0.0.1:5001/app/staff/reception |
| Patient: Eye Consultation | http://127.0.0.1:5001/app/b/erode-eye-clinic-demo/service/1 |
| Doctor sign in | http://127.0.0.1:5001/app/staff/login |
| Doctor queue | http://127.0.0.1:5001/app/staff/dashboard |
| Owner sign in | http://127.0.0.1:5001/app/owner/login |
| Owner dashboard and Today's Reviews | http://127.0.0.1:5001/app/owner/business/1 |
| Public Display | http://127.0.0.1:5001/app/b/erode-eye-clinic-demo/display |
| Monday completed consultation audit | http://127.0.0.1:5001/app/owner/business/1/history?date=2026-10-12&date_basis=finished&status=COMPLETED |

All URLs require the existing restricted browser gateway. Passwords are in ignored `.tmp\PRIVATE_LOCAL_DEMO_ACCESS.md`; Reception-only instructions are in `.tmp\PRIVATE_RECEPTION_ACCESS.md`. These files have permissions restricted to the current Windows user. Read them privately; do not share their contents, screenshots of them, or recovery links. Use separate browser profiles for Reception, Doctor, Owner and Patient.

Reception has an active Staff membership, with **no clinical assignment and no Owner rights**. Its authenticated read-only API scopes all services and QR codes to its active business membership. Doctor has an active Eye Consultation assignment; clinical actions continue to use existing service authorization and PostgreSQL locks. Mark Reviewed is the existing `COMPLETED` transition, with the original audit trail.

The dedicated QR endpoint creates a real PNG for the exact Eye Consultation service URL. Download saves that PNG. Print uses a QR-focused print layout. No placeholders or fabricated counts are used. For localhost preview, the QR contains `127.0.0.1:5001`; scanning it on another device requires the deferred networking phase.

## Start / restart

Keep the terminal open. Run this single command in PowerShell:

```powershell
& 'C:\Users\girin\.codex\worktrees\erode-monday-integration\DR\scripts\start-local-demo.ps1' -Action restart -Port 5001
```

Restart validates the saved process, its creation time, absolute script path and TCP listener before stopping only the candidate Flask server. It starts only the owned integration PostgreSQL cluster if necessary; it does not stop other database servers. The first start also works with `-Action start`. Stop the candidate Flask server with Ctrl+C in its own terminal.

The verified fallback remains at http://127.0.0.1:5000/app/ and `C:\Users\girin\.codex\worktrees\erode-local-demo\DR`. Restart its own launcher separately if needed. It still uses the original loopback PostgreSQL 55433 / `queueless_erode_demo`; its original 15 tickets are not reseeded or rewritten by candidate development.

## pgAdmin: register a separate server

Do not edit the `Digital ocean` registration or the fallback server.

| Setting | Integrated candidate |
| --- | --- |
| General / Name | QueueLess Pulse — Erode integration LOCAL PostgreSQL 18 |
| Host name/address | 127.0.0.1 |
| Port | 55434 |
| Maintenance database | queueless_erode_integration |
| Username | queueless_integration |
| Password | Private pgAdmin section of `.tmp\PRIVATE_LOCAL_DEMO_ACCESS.md` |
| SSL mode | Disable: loopback-only local database |
| Data directory | `.tmp\postgres18-data` in the integration worktree |

This additional cluster and its credentials are separate from the fallback. PostgreSQL listens only on loopback and uses SCRAM-SHA-256. The app role is not a superuser and cannot create roles/databases. Backend and baseline browser regression tests use a different database, `queueless_erode_integration_test`, with per-test schemas. The populated Erode browser acceptance uses separate `local_demo_check_...` schemas inside the candidate database; it verifies that the displayed public ticket/audit snapshot stays unchanged.

## Safe Monday preparation

Startup never resets tickets or changes their issue dates. Waiting and CALLED tickets survive midnight, continue in FIFO order, and an outstanding CALLED ticket must be finished before Call Next. Token numbering restarts per service and business-local date; a token number can recur on another date. Doctor and history screens show issue dates to distinguish these tickets.

Today's completed and skipped counts use the actual finish timestamp in the business timezone (`Asia/Kolkata`), including carried-over consultations. Today's Reviews includes only COMPLETED tickets, with the original issue date retained. History can filter either the issue date or review/skip date. Seven-day throughput retains its explicit ticket-business-date grouping; timing samples remain actual persisted events.

Before refreshing, stop the candidate Flask server, and use the private backup path returned by the command. On **Monday October 12**, inspect the read-only plan:

```powershell
Set-Location 'C:\Users\girin\.codex\worktrees\erode-monday-integration\DR'
& 'E:\Internship\New folder\DR\.venv\Scripts\python.exe' scripts/refresh_erode_demo.py --date 2026-10-12
```

Then explicitly apply it:

```powershell
& 'E:\Internship\New folder\DR\.venv\Scripts\python.exe' scripts/refresh_erode_demo.py --date 2026-10-12 --apply --resolve-carryover
```

The command checks the exact owned local cluster and fictional single tenant, creates a private verified PostgreSQL dump **before any change**, and completes older outstanding synthetic tickets through the existing Doctor workflow. It adds a new daily fixture of **7 completed, 2 skipped, 1 called and 5 waiting** using normal issuance/transitions. It never deletes tickets/audit events or backdates timestamps. Completion of six carried-over tickets adds six truthful completed consultations to that day's total: **13 completed today**, rather than a fabricated 7. Without carry-over, the total is 7.

The refresh is idempotent by date and request keys. It refuses future/backdated dates and refuses to overwrite an already-active current-day demonstration. An interrupted refresh records its progress and can resume only its own known requests; unexpected data causes it to stop. A refresh lock prevents simultaneous refresh commands. Inspect a stale lock privately rather than bypassing it automatically. Backups are in ignored `.tmp\backups`. Re-run startup after refresh.

## Short presentation

1. Reception: sign in, show the actual service QR, five waiting and E010 serving; demonstrate Download QR and the print preview.
2. Patient in a separate browser: open the service link and Join Queue. A fresh daily fixture issues E016, with six people ahead and an initial estimated 30-minute wait.
3. Doctor: Mark Reviewed on the already-called E010. Call Next calls E011, not E016. Skip E011; review E012–E015 in FIFO order, then call E016.
4. Patient and Reception/Public Display update automatically. Mark Reviewed on E016. Owner's Today's Reviews and date-filtered audit show its CREATED → CALLED → COMPLETED events.

This takes about two minutes when the browser profiles are already signed in. Later runs show the actual next token and current queue; they are never silently reset for the presentation.

## Verification and scope

Final local results: **130 passed, 0 failed, 0 skipped** (116 Python/backend/browser + 14 frontend). PostgreSQL concurrency, tenant isolation, role checks, desktop/mobile workflow acceptance and axe checks passed. Strict TypeScript, ESLint, production build, dependency audits and secret scans passed. The running persisted candidate also passed 10 interface-view checks and two print-layout checks without changing tickets.

Current candidate: 30 preserved/additive records, five waiting, one called; Sunday has 13 completed consultations and two skipped, including six truthful carry-over completions. The fallback still has its original 15 records and 34 audit events unchanged. Backup restoration was verified in an additional disposable database.

Screenshots in `evidence`: `live-reception-1366.png`, `live-reception-390.png`, `live-doctor-1366.png`, `live-patient-entry-390.png`, `live-owner-reviews-1366.png`, `live-public-display-1366.png` and `live-qr-print-390.png`. The private token recovery field is masked in ticket acceptance screenshots.

Run the reproducible full gate while the candidate is running with its fresh daily fixture (E010 called, five waiting):

```powershell
Set-Location 'C:\Users\girin\.codex\worktrees\erode-monday-integration\DR'
& 'E:\Internship\New folder\DR\.venv\Scripts\python.exe' scripts/verify_erode_local.py
```

Evidence is in ignored `evidence`: complete JUnit results, frontend JUnit, advisory reports, secret scans, database identity evidence and desktop/mobile screenshots. Browser tests use disposable schemas; they compare the public demo's ticket/audit snapshot before and after and do not alter displayed records. Accessibility checks cover WCAG A/AA rules through axe; these automated checks do not replace a complete human accessibility audit.

Physical Android, hotspot networking, certificate installation, APK packaging and cloud deployment are **deferred by user instruction**, not failed. HTTP is bound to laptop loopback for this phase. No production credentials, anonymous gateway removal or general commercial launch approval are involved.
