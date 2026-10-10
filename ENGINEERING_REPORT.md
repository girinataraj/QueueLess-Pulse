# Engineering Verification — QueueLess Pulse Universal Edition

Verified 2026-10-10, Asia/Kolkata. Root: `E:\Internship\New folder\DR`. `QueueLess_MVP` remains untouched.

## Completion

**Ready for deployment after the user's local UI inspection.** Final integrated execution: **73 passed, 0 failed, 0 skipped in 131.45 seconds**. All original 34 scenarios remain. Customer, Staff, Owner and Public Display workflows work in executed desktop/mobile browser tests. Tenant isolation, real PostgreSQL concurrency, migrations and production-like startup pass. No known critical defect remains in the verified scope. README and TESTING_REPORT are current.

Hosting is deliberately paused by user instruction. No GitHub publication, Render deployment, Neon schema change, production owner provisioning or verified live URL is claimed. A Neon connection check required a project ID; no project/database was created or changed. Authentication retains the existing hashed-password/signed-session design with scoped memberships.

## Implementation

| Interface | Implemented and verified |
| --- | --- |
| Customer | Scoped landing/QR entry; anonymous daily tickets; replay protection; private recovery/browser history; serving/position/ETA; five states and authorized cancellation |
| Staff | Active memberships/service assignments; secure login/logout; live assigned queues/waiting lists; call/complete/skip; one active ticket; mobile PWA |
| Owner | Registration/login; multiple businesses; branches/services/configuration/activation; staff/invitations; assignments/revoke; QR; live counts/measured timing/throughput/history |
| Public Display | Scoped business/branch tokens/services/counters; refresh/full-screen/reconnection; no private customer identifiers |

Shared navy/teal/off-white responsive design, accessible forms, loading/errors and safe cache. No frontend framework introduced. `models.py` adds Business, Branch, Membership, ServiceAssignment, StaffInvite and AdminEvent while preserving tickets/events. `access.py` centralizes scope checks; `universal.py` implements management/public/QR/analytics. `app.py` preserves factory/queue locking/CSRF, adding recovery/live fragments/timing/migration CLI. Fresh initialization creates no default credentials.

## Isolation and database safety

Private queries validate current owner membership or staff service assignment and scope requested targets to the business. Forged IDs do not grant access. PostgreSQL rejects cross-business assignment rows. Revocation locks affected service rows to serialize queue operations. Invitations are hashed, expire in 24 hours, accepted once, grant no automatic service access and cannot restore revoked membership.

Stable service-row locks serialize issue/call/complete/skip/cancel through commit/rollback. Daily uniqueness `(service_id,business_date,daily_number)` combines immutable service -> branch -> business scope. Partial unique index allows one CALLED ticket per service across dates. FIFO uses issuance IDs, dates use business IANA timezone. Timezone edits are denied after history. Inactive queues reject new joins while outstanding tickets can drain.

Upgrade CLI inspects schema and applies required 001/002/003 migrations in one PostgreSQL transaction. Legacy services/staff attach to Existing business/Main Branch; IDs/tokens/passwords/events/assignments survive. No owner is invented. Timing is backfilled only from real events. Conflicting historical numbering aborts and rolls back. Valid/conflicting legacy upgrade and previous audited-schema upgrade were tested. Current schema is an idempotent no-op.

## Security and evidence

Hashed passwords, explicit active roles, CSRF mutations, POST logout, secure production cookies, input constraints, escaped templates/safe DOM, no private caching, bearer-link referrer policy and explicit rollback/error responses. Production requires PostgreSQL/strong secret. Runtime startup does no DDL; health checks required schema/connectivity.

73 cases: 22 original unit/config/CLI, 34 Universal functional, 13 real PostgreSQL, four browser. Evidence: `universal-final.xml/.log`. Compilation/pip consistency passed. Advisory scan found no known vulnerabilities (`universal-dependency-audit.json/.log`); it is not proof of complete vulnerability absence. TESTING_REPORT maps scenarios, exact commands, failures/retests and screenshots. CI is provided, not yet executed on GitHub.

Analytics use persisted call/finish timestamps and exclude missing samples; ETA uses configured fallback duration and is approximate. Admin/queue actions create scoped audit events; no database-admin tamper resistance is claimed.

## Remaining scope and deployment checks

No known failing test or unfinished requested MVP workflow remains. Invitations are manually shared; email delivery is absent. Ticket view is bearer-link access; cancellation requires issuing-session ownership. SQLite preview is single-process; legacy SQLite upgrade is not automated. Login throttling/password reset, backups/monitoring, abuse control, cloud outage/load testing, APK/push and multi-counter operation remain outside verified MVP.

Local PWA manifests, registration/cache policy/mobile flows pass. Hosted HTTPS prompts/physical Android installation await hosting. Windows cannot run Gunicorn natively; Linux CI/Render launch, Neon runtime connection, restart persistence and hosted workflows remain deployment-stage verification. No live URL exists at this stage.

## Local preview

Exact PowerShell commands in TESTING_REPORT and README use existing `.venv`, separate `universal-preview.db`, private process secret and loopback port 5000. Register at `/owner/register`; configure business/branch/service/staff and permissions. Inspect customer `/`, staff `/staff/login`, owner `/owner` and reception `/display` in separate browser profiles.

After UI inspection and user instruction to resume: prepare/publish root repository, configure Neon/Render Free secrets, initialize/upgrade safely, provision owner, launch Gunicorn, verify actual HTTPS health/all four flows/isolation/restart/PWA. These external actions remain pending.

## CI fixture correction (2026-10-10)

The original GitHub Linux run intermittently exited 139 during browser tests because its threaded server shared the in-memory SQLite fixture connection. Browser tests now use isolated file databases with separate pooled connections and proper server cleanup. A regression proves connection/transaction independence. All original 73 scenarios remain, plus one regression: **74 passed, 0 failed, 0 skipped in 153.196 seconds** in the full local run. Dependency audit found no known vulnerabilities. See [CI_INVESTIGATION.md](CI_INVESTIGATION.md) for original run evidence, reproduction and fix boundaries. The workflow and production application remain unchanged.
