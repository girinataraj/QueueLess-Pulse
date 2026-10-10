# Frontend migration plan

Baseline: PR #1 merged as `d8c22d4187c5f14ba804fe416c9c891b49b6faba`; 74 local tests passed with no skips; post-merge Actions run 38031534827 passed. Work is on `feat/react-typescript-frontend`. No deployment or automatic migration merge.

## Audited implementation and consumers

Inspected `app.py`, `universal.py`, `access.py`, `models.py`, all 20 Jinja templates, inline polling scripts, CSS, manifest/worker, three migrations and seven test modules. The root application is authoritative; QueueLess_MVP is untouched. Route names below come from Flask's actual URL map.

| Existing route family | Methods / consumer | Behavior retained |
| --- | --- | --- |
| `/`, `/b/<slug>`, `/b/<slug>/branch/<id>`, `/b/<slug>/service/<id>` | GET customer directory/business/selection and QR | Active business, branch and service scope |
| `/service/<id>/join` | POST service cards | UUID replay key, service-row lock, business date, ticket/audit commit |
| `/ticket/<token>`, `/ticket/<token>/status`, `/ticket/<token>/cancel`, `/my-tickets` | GET tracking/status/history; POST cancellation | Bearer viewing, issuing signed-session cancellation, 30 recent links |
| `/staff/login`, `/staff/logout`, `/staff/dashboard`, `/staff/live`, `/staff/fragment` | GET/POST login, POST logout, GET dashboard/poll/fragment | Active identity, scoped assignments, live queue cards |
| `/staff/call/<id>`, `/staff/complete/<id>`, `/staff/skip/<id>` | POST staff controls | Same service lock, one CALLED, FIFO, transitions and audit |
| `/owner/register`, `/owner/login`, `/owner` | GET/POST auth; GET business list | Existing hashed account/signed-session establishment |
| `/owner/business/create`, `/owner/business/<id>/edit` | POST owner forms | Slug/profile/timezone validation; timezone locked after history |
| `/owner/business/<id>`, `/stats`, `/history` | GET dashboard/JSON metrics/paginated history | Owner-only scope, real timing and seven-day throughput |
| business `/branches/create`, `/branches/<id>/edit`, `/services/create`, `/services/<id>/edit` | POST management | Scoped targets, serialized config, activation and validation |
| business `/staff/create`, `/staff/<id>/permissions`, `/staff/invite` | POST management | Unassigned creation, scoped assignment/revoke, hashed 24-hour invitation |
| `/invite/<token>` | GET/POST invitation | One use, expiry, no restored revoked membership, no email transport |
| business `/qr.png` | GET owner image/download | Business/branch/service scoped URL, canonical origin |
| `/display`, `/api/display_data`, `/b/<slug>/display`, `/b/<slug>/api/display` | GET reception directory/display/poll | Public serving numbers only, scoped branch, drain inactive outstanding queues |
| `/health`, `/sw.js`, `/staff/manifest.webmanifest`, `/static/*` | GET monitoring/PWA/assets | Schema/connectivity, safe static allowlist, staff start URL |

## Parity inventory and planned verification

| Experience | React modules | Required parity / test evidence |
| --- | --- | --- |
| Customer | directory, business/services, ticket, browser history | QR entry, anonymous join/replay, live serving/position/ETA, all states, cancel/recovery, mobile/errors |
| Staff | auth, queues | Assigned queues, ordered waiting list, call/complete/skip, one active, forbidden/expired session, polling/reconnect |
| Owner | auth, businesses, operational dashboard, management forms, history/invitation | Profiles, branches, service config/activation, staff/permissions/invites, scoped QR, actual metrics/throughput/history |
| Reception | display directory and scoped screen | Branch scope, token/service/counter, fullscreen, polling/reconnect, no private IDs |

The matrix is a plan, not a claim that these milestones have already passed. Existing Jinja routes and all 74 baseline scenarios stay runnable. New API tests, strict TS/lint/component/form/error-boundary/accessibility tests, production build and PostgreSQL-backed desktop/mobile React workflows establish parity before any replacement.

## Authentication, CSRF and queue contract

Keep Flask signed HttpOnly/SameSite session cookies, Secure in production. No JWT or localStorage credentials. Session bootstrap creates the existing anonymous owner ID and CSRF token. Login clears/rotates session; the client reloads bootstrap after auth. Every mutation, including anonymous join/auth, includes the existing form CSRF token. Server membership/assignment checks remain authoritative. All API responses are no-store, private links use no-referrer. UI cache is cleared on login/logout so identities cannot inherit private TanStack Query data.

States: WAITING → CALLED → COMPLETED or SKIPPED; WAITING → CANCELLED by issuing session. Repeated same terminal operation is idempotent; conflicting transitions return 409. Stable service row lock, daily unique numbering, one-active index, UUID request keys, PostgreSQL READ COMMITTED and audit commits remain in the existing handlers. API adapters invoke the same handlers rather than copying queue transactions.

## Versioned endpoints and typed schemas

New `/api/v1` endpoints use JSON responses. Mutations deliberately accept URL-encoded fields (the audited validators' existing input contract), including repeated `service_ids` and `is_active=on`; this keeps one validation/transaction implementation. JSON input is not silently accepted. Error envelope: `{error: {code: string, message: string}}` with 400/401/404/409/410/503 as applicable. Success statuses are explicit, and redirects become JSON results with a resource path.

- GET `/session`: CSRF, nullable account and active memberships.
- POST `/auth/register`, `/auth/login`, `/auth/logout`: same accounts and session mechanics.
- GET `/businesses`, `/businesses/<slug>`: public profiles/active branches/services.
- POST `/services/<id>/tickets`; GET `/tickets/<token>`, `/my-tickets`; POST `/tickets/<token>/cancel`: private ticket representation with state/business/service/date/cancel authority.
- GET `/staff/queues`; POST `/staff/services/<id>/call`, `/staff/tickets/<id>/complete|skip`.
- GET/POST `/owner/businesses`; GET/POST `/owner/businesses/<id>`; POST scoped `/branches`, `/branches/<id>`, `/services`, `/services/<id>`, `/staff`, `/staff/<membership>/permissions`, `/invitations`; GET `/history` and `/stats`.
- GET/POST `/invitations/<token>`; GET `/display/<slug>?branch_id=<id>`.
- Owner QR remains an authenticated binary endpoint; a controlled `ui=react` selector creates `/app` entry links without changing old QR behavior.

Single source response schemas live in `contracts/api.schema.json`. Generated TypeScript types are committed and checked for drift; backend response contract tests validate against that same schema. Mutation field schemas are shared by domain forms and documented in the API module. Do not expose session owner IDs, password hashes or ticket bearer tokens in public/display/staff feeds.

## Migration sequence and hosting

1. Add contracts/API/session integration and Vite/React tooling; keep legacy unchanged.
2. Customer routes/components and tests.
3. Staff console.
4. Owner management, analytics/history/invites.
5. Public display.
6. Full parity/accessibility/security/PostgreSQL/desktop/mobile/build verification; dedicated PR with real screenshots and results.

Serve React at `/app` and `/app/*` from Flask after Vite build. Vite uses base `/app/`, a dev proxy to loopback Flask, and assets with content hashes. Unknown API paths remain JSON errors, never SPA HTML. One root service worker serves both UIs; it caches only the existing public CSS/icons and never navigation, confidential API data or authentication. React has its own manifest start URL but no competing worker. Preserve legacy paths for rollback and existing QR links. Render deployment stays paused; frontend build/Gunicorn integration is documented and verified locally/CI only.

## Risks and rollback

Rollback is immediate: use the existing Jinja routes or revert the migration branch; no destructive schema migration or queue-data changes. React remains opt-in until parity is verified. Major risks are stale CSRF after login, cross-identity client cache, overbroad SPA fallbacks, double-issued tickets after retry, polling overload, privacy leakage in display feeds, test fixture concurrency and serving stale chunk versions. Tests cover these boundaries; mutations reuse replay keys, polling is bounded and requests are never cached by the worker.

No compliance certification is claimed. Privacy/terms identity/contact, retention policy, deletion/export/account recovery, login throttling, backups/monitoring and hosting operations remain unimplemented controls; do not invent legal promises or fake analytics. Device install prompts and deployment behavior remain unverified until authorized hosting.

## Approved release-candidate scope change (2026-10-10)

The user explicitly changed the objective to a restricted evaluator release and required authentication/issuance rate limiting. The migration therefore adds shared atomic database counters, safe additive migration 004, an environment-controlled outer demo gate and reproducible Render build/start configuration with auto-deploy off. This is additional release security, not a queue-engine rewrite. The legal audience is invited evaluators/testers with synthetic data only; operator/privacy contact/reviewed policy remain unresolved. Factual drafts and deployment blockers are in docs/legal and RELEASE_RUNBOOK.md. No unrestricted real-customer launch is authorized.
