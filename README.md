# QueueLess Pulse Universal Edition

## Live Demo & Android App

**Live Web Application:** [https://queueless-pulse-staging-free.onrender.com/app/](https://queueless-pulse-staging-free.onrender.com/app/)

**Android APK:** [Download the signed Android v0.2.1 staging APK](https://github.com/girinataraj/QueueLess-Pulse/releases/download/v0.2.1-android-staging/QueueLess-Pulse-Android-HTTPS-Launch-v0.2.1.apk)

**GitHub Releases:** [QueueLess Pulse Android v0.2.1 — Staging Demo](https://github.com/girinataraj/QueueLess-Pulse/releases/tag/v0.2.1-android-staging)

Render Free hosting can cold-start; allow the application time to wake. Patient and Public Display can be viewed without role login. Reception, Doctor and Owner require authorized accounts. The connected Android app requires internet access; physical-device testing is not yet verified.

Only synthetic demonstration data is used. This staging demo is not approved for real patient information or clinical operations.

A multi-business virtual queue platform for clinics, salons, banks, offices and service centers. The authoritative code is this `DR` root. The older `QueueLess_MVP/` directory is preserved untouched and excluded from the production repository.

## Four connected experiences

- **Customer:** business landing → branch → service, QR entry, registration-free ticket, private recovery URL/browser ticket history, live position/estimated wait/current serving, owner-session cancellation and all five states.
- **Staff:** hashed-password login, explicit business memberships and service permissions, assigned queues/waiting lists, call/complete/skip, live dashboard, clear empty/error states and staff PWA manifest.
- **Owner:** registration/login, multiple business profiles, branches, service names/prefixes/fallback durations/counter labels, activation, secure staff creation or one-time invitations, permission assignment/revocation, business/branch/service QR downloads, live counts, actual timing averages, seven-day throughput and paginated completed/skipped audit history.
- **Reception:** public display per business/branch, current serving token/service/counter, automatic refresh, full-screen control and connection status. No private recovery tokens, identities or customer ownership IDs are returned.

Shared navy/teal/off-white design and mobile layouts. The React + strict TypeScript interface runs at `/app/`; the original Jinja interface stays available at `/` for rollback. Single active ticket per service. QR codes open scoped entry pages and were decoded during real browser verification. Approximate queue waits use configured service duration; historical timing averages use recorded call/finish timestamps and show no-data explicitly.

## Local development — Windows PowerShell

### Preview with the existing environment

PR #1 established a green **74-test baseline** after the SQLite browser-fixture correction. The React migration adds API, component and PostgreSQL browser verification; see [Frontend verification](docs/FRONTEND_VERIFICATION.md) for current exact results. The hosted staging demo is linked above; local preview remains available independently. From this workspace, run:

Local execution logs, JUnit files and screenshots remain in `evidence/`, which is excluded from Git publishing. Reports preserve the verified results and commands; CI can generate fresh evidence as downloadable artifacts.

```powershell
Set-Location -LiteralPath 'E:\Internship\New folder\DR'
$env:APP_ENV='development'
Remove-Item Env:RENDER -ErrorAction SilentlyContinue
$env:DATABASE_URL='sqlite:///universal-preview.db'
$env:SECRET_KEY=(& .\.venv\Scripts\python.exe -c 'import secrets; print(secrets.token_hex(32))')
$env:PUBLIC_BASE_URL='http://127.0.0.1:5000'
$env:TRUSTED_HOSTS='127.0.0.1,localhost'
& .\.venv\Scripts\python.exe -m flask --app app initdb
& .\.venv\Scripts\python.exe -m flask --app app run --host 127.0.0.1 --port 5000
```

Open [Owner registration](http://127.0.0.1:5000/owner/register), create your own owner, business, branch and service, then create staff and assign that service. Inspect [Customer](http://127.0.0.1:5000/), [Staff](http://127.0.0.1:5000/staff/login), [Owner](http://127.0.0.1:5000/owner) and [Display](http://127.0.0.1:5000/display) using separate browser profiles. No default credentials are created. Keep this terminal open to retain its secret; Ctrl+C stops the server. Generating another secret invalidates old sessions but preserves preview data. SQLite preview is single-process only; PostgreSQL concurrency was verified separately.

### Recreate the environment if needed

Python 3.12 is required. The already installed bundled runtime was used without changing system PATH:

```powershell
& 'C:\Users\girin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m venv .venv
New-Item -ItemType Directory -Force .tmp | Out-Null
$env:TEMP=(Resolve-Path .tmp).Path
$env:TMP=$env:TEMP
# Only needed if venv's pip bootstrap failed due to TEMP permissions:
& .\.venv\Scripts\python.exe -m ensurepip --upgrade
& .\.venv\Scripts\python.exe -m pip install pip==26.2.1 -r requirements-test.txt --index-url https://pypi.org/simple
Copy-Item .env.example .env
# Generate a secret, copy it privately into .env:
& .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
& .\.venv\Scripts\python.exe -m flask --app app initdb
& .\.venv\Scripts\python.exe -m flask --app app run
```

`initdb` creates the Universal schema only: **no default account, business or service**. Open `/owner/register`, create your account/business, add a branch/service, then create or invite staff and assign permissions. Never commit `.env`. SQLite is local single-process development only; it does not establish PostgreSQL concurrency correctness.

## Routes and demonstration

| Purpose | Route |
| --- | --- |
| Business directory | `/` |
| Customer business / branch / service QR entry | `/b/<slug>`, `/b/<slug>/branch/<id>`, `/b/<slug>/service/<id>` |
| Private ticket / status / cancellation | `/ticket/<token>`, `/ticket/<token>/status`, POST `/ticket/<token>/cancel` |
| Browser-owned recent ticket links | `/my-tickets` |
| Staff login / dashboard / live data | `/staff/login`, `/staff/dashboard`, `/staff/live` |
| Owner register / login / businesses | `/owner/register`, `/owner/login`, `/owner` |
| Owner management / history / stats / QR | `/owner/business/<id>`, `/history`, `/stats`, `/qr.png` appended to that business URL |
| Scoped reception display / public data | `/b/<slug>/display?branch_id=<id>`, `/b/<slug>/api/display?branch_id=<id>` |
| Readiness | `/health` |

Demo: register an owner → create business/branch/service → create staff and assign that service → download/scan its QR on a phone → join → log in as staff in another browser → call → observe customer/reception/owner updates → complete → show owner history/real metrics. Invite links last 24 hours, are hashed at rest, accepted once and grant no service access automatically. Share them privately; the app does not send email. Existing users may sign in, reopen and accept; an old invitation cannot restore revoked membership.

Ticket URLs are deliberate bearer recovery links: anyone holding the URL can view that one ticket, while cancellation additionally requires the issuing browser's signed session. Login preserves the customer identity in that browser; logout/session loss removes cancellation access. `/my-tickets` never accepts a customer identity from a request parameter.

## Data isolation and queue transactions

`Business → Branch → Service → Ticket → TicketEvent`. Identities have explicit `Membership` rows (`owner` or `staff`) and `ServiceAssignment` rows. Private management queries validate owner membership and scope every target to that business. Staff queues/actions validate current active membership and assignment. PostgreSQL also rejects cross-business assignment rows with a trigger. No business role is accepted from browser session/payload fields.

Services remain in their branch; owner edits never move historical queues to another tenant. Unique `(branch_id, name)` / `(branch_id, prefix)` constraints allow another branch/business to configure the same service safely. The ticket unique key `(service_id, business_date, daily_number)` identifies one immutable business/branch/service scope through foreign keys. A partial unique index permits one CALLED ticket per service across all dates.

Issuance, call, complete, skip and cancellation use the same stable service-row lock, held through commit. Staff permissions and service/branch configuration changes serialize on those service rows. READ COMMITTED PostgreSQL is the supported isolation level. No SKIP LOCKED, implicit completion or history deletion is used. FIFO uses IDs allocated under the service lock; daily numbering uses each business's IANA timezone. Timezone changes are prohibited after ticket history exists. Inactive branches/services stop new joins while staff/reception can drain outstanding tickets.

Configuration changes write business-scoped admin audit events; queue transitions write immutable event history through the application. Actual timing fields are backfilled from historical events during upgrade when such events exist; missing historical timing is excluded rather than invented.

## Safe database upgrades

Back up and stop traffic before upgrading an existing PostgreSQL database. Set DATABASE_URL, SECRET_KEY and BUSINESS_TIMEZONE for the intended database; then:

```powershell
& .\.venv\Scripts\python.exe -m flask --app app upgrade-db --apply
```

The CLI inspects the existing schema and executes the necessary SQL files in one transaction: `001_queue_integrity.sql` (original numbering/security schema), `002_universal.sql` (business/branch/memberships/timing), `003_assignment_guard.sql` (PostgreSQL assignment scope). `migrate-legacy --apply` remains a compatible alias. Fresh deployments use `initdb` instead.

Existing IDs, ticket numbers, tokens, passwords and ticket events survive. Old services and staff are attached to an **Existing business** (`/b/legacy`) and **Main Branch**; old staff retain service assignments. No owner is created automatically. After upgrade, claim that business securely:

```powershell
& .\.venv\Scripts\python.exe -m flask --app app create-owner --business-id 1 --username YOUR_NAME
# Password is prompted privately. For an existing identity, its current password must match.
```

Use the actual legacy business ID from the database if it differs. A newly created owner password must have at least 12 characters. `create-staff --business-id <id> --username <name>` is a trusted administrator CLI that assigns all current services in the chosen business; owner UI staff creation starts unassigned.

Pre-existing duplicate daily numbers or multiple CALLED tickets abort the whole upgrade. Inspect and resolve conflicts explicitly without deleting history. Original naive timestamps are interpreted as UTC before deriving business dates. Migrated customer cancellation ownership cannot be recovered from the old app. Legacy SQLite upgrades are not automated; export into PostgreSQL with explicit review. `initdb` refuses legacy schemas rather than silently altering or dropping them.

## Verification

```powershell
$env:TEMP=(Resolve-Path .tmp).Path
$env:TMP=$env:TEMP
$env:TEST_DATABASE_URL='postgresql+psycopg2://USER:PASSWORD@HOST:PORT/queueless_test'
$env:PLAYWRIGHT_EXECUTABLE_PATH='C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
# Or install Chromium with python -m playwright install chromium and leave the override unset.
& .\.venv\Scripts\python.exe -m compileall -q app.py models.py config.py access.py universal.py tests
& .\.venv\Scripts\python.exe -m pytest -q --junitxml=evidence/universal-final.xml
& .\.venv\Scripts\python.exe -m pip check
& .\.venv\Scripts\python.exe -m pip_audit --format json --output evidence/universal-dependency-audit.json
```

The PostgreSQL database must have a name ending `_test`; every integration case creates/removes only a random schema there. **Never set TEST_DATABASE_URL to production.** Browser tests launch their own server with isolated test fixtures. CI runs the same suite with PostgreSQL and Chromium; the merged baseline workflow has passed on GitHub; migration run results are recorded in the frontend verification report. Final execution counts/failures/retests are in TESTING_REPORT.md; screenshots/JUnit/advisory evidence is in `evidence/`.

## Production deployment — after the local completion gate

No hosting has been performed yet. GitHub/Neon/Render account access and the real HTTPS URL are external requirements.

1. Push this authoritative root to a GitHub repository. Exclude `.env`, `.venv`, `.tmp`, `instance`, databases and `QueueLess_MVP`. Keep migrations, root templates/static files, tests, CI and reports. Select this app.py directory as Render Root Directory.
2. Create/select a free Neon PostgreSQL database. Preserve `sslmode=require` in the URL. Set secrets through local environment/Render settings; never paste credentials into source, logs or commits.
3. Initialize a fresh database with `python -m flask --app app initdb`, or back up and apply `upgrade-db --apply` to existing data. Run these using the local venv with the intended DATABASE_URL, because Render Free remote shell access is unavailable.
4. The restricted-demo `render.yaml` builds Python and the pinned React frontend through `bash scripts/render-build.sh`; starts Gunicorn with two workers/four threads, loopback-independent `$PORT` binding and logs that omit request URLs/auth headers; uses `/health`; and keeps automatic deployment off. Approve the PR before merging/deploying. See [release runbook](docs/RELEASE_RUNBOOK.md).
5. Set `PYTHON_VERSION=3.12.14`, `APP_ENV=production`, `DATABASE_URL`, generated `SECRET_KEY` (at least 32 characters) and `BUSINESS_TIMEZONE=Asia/Kolkata` (legacy/default context only; new businesses configure their own timezone). Set `PUBLIC_BASE_URL` to the actual HTTPS origin after Render assigns it. Set `TRUSTED_HOSTS` to accepted hostnames appropriate for public traffic and health checks. These settings ensure canonical QR/invitation URLs and optional Host-header validation. PostgreSQL URLs normalize to the declared psycopg2 driver; production rejects SQLite and absent/short secrets.
6. Register the initial owner through HTTPS and configure business/branch/service/team. For migrated history use the private create-owner CLI. No default production credentials exist.
7. Verify the actual hosted `/health`, all four workflows across separate browsers, two-business access denial, persistence after restart, mobile layouts, staff/main PWA manifests, HTTPS worker registration/install prompt and private cache policy. Only then describe hosting as successful.

Render Free spins down after 15 idle minutes and has ephemeral local storage; queue data must reside in PostgreSQL. Gunicorn is a Linux dependency and cannot launch natively on Windows. The local production-config PostgreSQL test does not prove Render process startup. Free-tier quotas and availability must be checked in the actual provider accounts.

Sources: [Render Flask](https://render.com/docs/deploy-flask), [Render Free](https://render.com/docs/free), [Render services](https://render.com/docs/web-services), [PostgreSQL row locks](https://www.postgresql.org/docs/18/explicit-locking.html). Provider instructions were checked during the preceding audit; verify account-specific options at deployment.

## PWA and operational scope

Main manifest starts at `/`; staff manifest starts at `/staff/dashboard`. Icons are 192/512 PNGs. The root service worker caches **only** CSS and those two icons, cleans obsolete caches and never stores staff, owner, ticket, invitation, HTML or API responses. Live operations require a network. Local browser tests verify manifests/worker/static cache/mobile workflows; actual hosted install prompts and Android behavior require HTTPS verification.

This is a complete shortlist/demo MVP, not a certified critical-service product. The signed Android staging APK is linked above. Multi-counter operation, payments, push subscriptions and personal customer identity collection remain outside scope. Database-backed authentication/queue rate limiting is now implemented. Backups, monitoring, abuse controls and cloud outage/load testing remain operational hardening tasks before wider real-world use.

## React frontend preview and architecture

The migration is additive: `/app/*` serves the React build; `/api/v1/*` adapts the same audited Flask handlers. Models, PostgreSQL locks, migrations and tenant checks remain authoritative. Original templates, QR links and routes remain available. See [migration audit](docs/FRONTEND_MIGRATION_PLAN.md), [API contracts](docs/API_CONTRACT.md) and [verification/limitations](docs/FRONTEND_VERIFICATION.md).

Use Node 24 and pnpm 11.25.0. On this machine the installed bundled tools can build without changing system PATH permanently:

```powershell
Set-Location -LiteralPath 'E:\Internship\New folder\DR'
$env:PATH='C:\Users\girin\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin;'+$env:PATH
$pnpm='C:\Users\girin\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback\pnpm.cmd'
& $pnpm --dir frontend install --frozen-lockfile --strict-peer-dependencies --store-dir .tmp/pnpm-store
& $pnpm --dir frontend run typecheck
& $pnpm --dir frontend run lint
& $pnpm --dir frontend run test
& $pnpm --dir frontend run build
$env:APP_ENV='development'
Remove-Item Env:RENDER -ErrorAction SilentlyContinue
$env:DATABASE_URL='sqlite:///universal-preview.db'
$env:SECRET_KEY=(& .\.venv\Scripts\python.exe -c 'import secrets; print(secrets.token_hex(32))')
$env:PUBLIC_BASE_URL='http://127.0.0.1:5000'
$env:TRUSTED_HOSTS='127.0.0.1,localhost'
& .\.venv\Scripts\python.exe -m flask --app app initdb
& .\.venv\Scripts\python.exe -m flask --app app run --host 127.0.0.1 --port 5000
```

Then inspect [React Customer](http://127.0.0.1:5000/app/), [React Staff](http://127.0.0.1:5000/app/staff/login), [React Owner registration](http://127.0.0.1:5000/app/owner/register), [React Owner](http://127.0.0.1:5000/app/owner) and [React Display directory](http://127.0.0.1:5000/app/display). Configure your business/branch/service and staff permissions in the owner workspace. Use separate browser profiles for each role. No demo passwords or accounts are created. Existing local preview data can be reused; do not run the unrelated local `seed.py`. SQLite preview is single-process only.

For hot reload, keep Flask on 5000, and run `pnpm --dir frontend dev` in a second terminal. Open `http://127.0.0.1:5173/app/`. Vite proxies API, authenticated QR, icons, manifest and the single root service worker to Flask. Set PUBLIC_BASE_URL to the frontend origin if generating QR/invitation links for that development session; use the Flask-served production build for the closest one-origin preview.

For a later Linux production build, install the pinned frontend with `pnpm --dir frontend install --frozen-lockfile --strict-peer-dependencies`, then `pnpm --dir frontend run build`, and install Python requirements. Serve `app:app` with the existing Gunicorn command and real production environment. Flask serves `frontend/dist` assets and deep links from that one origin; no frontend secret is compiled into JavaScript. CI smoke-tests production PostgreSQL configuration with two Gunicorn workers and four threads. No cloud deployment is performed by this migration. The updated Render blueprint supplies the reproducible frontend build, production configuration and restricted-demo gate; account-specific and hosted workflow verification still precede any live claim.

React uses `/app.webmanifest` (start/scope `/app/`) and the existing root worker. Only public CSS/icons are cached; confidential responses and navigation remain network-only. Browser manifests, registration and cache policy are tested; physical Android installation and hosted HTTPS prompts remain deployment-stage checks.

## Restricted demonstration release

The authorized audience is technical evaluators, project reviewers and privately invited testers using fictional profiles and synthetic tickets only. A formal legal operator, privacy contact and reviewed terms/retention policy are unresolved. Real customer data, unrestricted public registration and general commercial use are launch-blocked. Drafts in [docs/legal](docs/legal) describe actual behavior without compliance claims.

`DEMO_MODE=true` requires environment-supplied `DEMO_ACCESS_USER` and `DEMO_ACCESS_PASSWORD` (at least 32 characters). This outer HTTP Basic gate protects both UIs/APIs/assets/registration, with `/health` as the sole GET/HEAD exception; it grants no application role and bypasses no CSRF check. Share evaluator access privately over HTTPS, never through source or public demo credentials. The React session shows a factual synthetic-data notice. Production also requires the existing strong SECRET_KEY, PostgreSQL, Secure/HttpOnly/SameSite cookies and no debug mode.

Authentication endpoints share a per-address limit of 30 POST attempts per five-minute fixed window; legacy/React ticket creation share 120 POST attempts per minute. HMAC identifiers and atomic database counters are shared by Gunicorn workers; limits return 429/Retry-After and database failure fails closed as 503. Forwarded headers are ignored locally (`RATE_LIMIT_TRUSTED_PROXY_HOPS=0`). The Render configuration sets one trusted appended hop, which must be checked against the live edge chain before reviewer access; never trust an arbitrary client-controlled first header value. Limits include successful requests and retries and may affect shared networks near the threshold; choose any tuning through reviewed environment settings. They do not constitute comprehensive DDoS protection.

Fresh `initdb` creates all tables without accounts. Existing PostgreSQL upgrades add `004_rate_limits.sql` through the backed-up `upgrade-db --apply` path; it adds only the limiter table/index and preserves identities, queues and audit history. No production database change is performed in this task before deployment approval.
