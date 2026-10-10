# React API contracts

All routes below are prefixed `/api/v1`. GET responses and mutation results are JSON and `Cache-Control: no-store`. State changes use **POST with application/x-www-form-urlencoded**, not JSON bodies. Fetch `/session` first and send its token in `X-CSRF-Token` (or the existing `csrf_token` form field). Cookies use the existing Flask signed, HttpOnly, SameSite=Lax session; Secure is required in production. Login, registration and invitation acceptance rotate the session/token. No JWT or browser-storage authentication is used.

## Mutation fields

These are the actual existing Flask validators invoked by the API adapters. Fields are strings on the wire. Optional empty strings are allowed unless noted. `is_active=on` enables a service/branch/membership; omit it to disable. Send multiple `service_ids` as repeated form keys, not a JSON array. Server authorization and validation are always authoritative.

| POST path | Request fields | Response / success |
| --- | --- | --- |
| `/auth/register` | username (3–64 letters/digits/underscore/dot/hyphen), password (12–128 characters), matching confirm_password; optional email (max 254, validated) | Session / 201 |
| `/auth/login` | username, password | Session / 200 |
| `/auth/logout` | No fields beyond CSRF | Session / 200 |
| `/services/<id>/tickets` | request_key (UUID; reuse for retries of this issuance) | Ticket / 201, including replay |
| `/tickets/<token>/cancel` | No fields beyond CSRF | Ticket / 200 |
| `/staff/services/<id>/call` | No fields beyond CSRF | Action / 200 |
| `/staff/tickets/<id>/complete`, `/skip` | No fields beyond CSRF | Action / 200 |
| `/owner/businesses` | name (1–128), slug (1–80 lowercase slug), category (1–40), timezone (valid IANA name, max 64), optional description (max 1000) | Action / 201 |
| `/owner/businesses/<id>` | name, category, timezone, description as above; slug is immutable; timezone cannot change after history | Action / 200 |
| owner business `/branches` | name (1–128), optional address (max 300); initially active | Action / 201 |
| owner business `/branches/<id>` | name, address, is_active | Action / 200 |
| owner business `/services` | branch_id (positive integer scoped to business), name (1–128), prefix (1–6 letters/digits), average_minutes (integer 1–120), optional counter_label (max 40), description (max 256), is_active | Action / 201 |
| owner business `/services/<id>` | Same service fields except branch_id; services cannot move branches | Action / 200 |
| owner business `/staff` | username/password/optional email as registration, without confirm_password | Action / 201; unassigned staff |
| owner business `/staff/<membership>/permissions` | is_active and repeated service_ids (positive integer IDs belonging to that business) | Action / 200 |
| owner business `/invitations` | No fields beyond CSRF | InviteCreated / 201; private one-use URL |
| `/invitations/<token>` | Registration fields if anonymous; no account fields when already signed in | Session / 200 |

`Action.resource_path` is the existing relative application destination; React Router adds its `/app` basename. The API calls the audited handlers directly, retaining validation, role checks, transaction boundaries, row locks and audit writes. It never follows legacy redirects over the network.

## Read contracts

`contracts/api.schema.json` is the response-schema source. `scripts/generate_contracts.py` generates `frontend/src/api/contracts.ts`; CI checks generation drift and Python contract tests validate actual responses. Domain form field definitions and the table above describe requests.

| GET path | Contract / scope |
| --- | --- |
| `/session` | Session: nullable identity, CSRF, current active memberships, demo_mode; no browser owner ID |
| `/businesses` | BusinessList: active public businesses |
| `/businesses/<slug>` | PublicBusiness: public profile, active branches/services |
| `/tickets/<token>` | Ticket: bearer recovery view; can_cancel additionally requires issuing browser |
| `/my-tickets` | TicketList: signed browser ownership only, latest 30 |
| `/staff/queues` | QueueList: current active assignments; queue ticket database IDs only for staff actions |
| `/owner/businesses` | BusinessList: current owner's businesses |
| `/owner/businesses/<id>` | OwnerBusiness: owner-scoped config, memberships/assignments and real stats |
| owner business `/stats` | Metrics: persisted counts, timing samples, seven-day throughput |
| owner business `/history?status=&service_id=&page=1` | History: completed/skipped tickets, 25 per page, owner-scoped service filter; no bearer tokens |
| `/invitations/<token>` | Invitation: business name only; expired/consumed returns 410 |
| `/display/<slug>?branch_id=<id>` | DisplayList: scoped service/branch/counter/serving number/waiting count; no bearer tokens/customer identity |

Owner QR downloads remain binary GET `/owner/business/<id>/qr.png?ui=react&download=1` with optional scoped `branch_id` or `service_id`. Existing QR URLs remain supported. Every private management target is checked on the server, including foreign IDs supplied in otherwise valid owner payloads.

## Errors and caching

JSON error envelope: `{ "error": { "code": "...", "message": "..." } }`. HTTP 429 means a shared auth/issuance rate limit, with Retry-After. HTTP 400 means invalid input/CSRF; 401 unauthenticated/invalid login; 403 forbidden; 404 missing or out-of-scope resource; 409 conflicting state/constraint/inactive issuance; 410 invitation expired/used; 415 wrong mutation media type; 503 database unavailable. Unexpected programming failures are not rewritten as success. React shows an error/retry state; it hides cached private data after 401/403/404/410. Public connection failures display stale values explicitly until polling recovers.

The existing root worker caches only public legacy CSS and two icons. It does not cache these APIs, either interface's HTML, login, invitation or ticket pages. All non-static responses are no-store, with no-referrer on private URLs. The SPA fallback handles `/app` paths only; unknown API routes remain JSON 404 and missing asset paths remain 404.

## Restricted evaluator gate

With DEMO_MODE=true, private evaluator HTTP Basic authorization is required for both UIs, all APIs, registration, assets and worker requests. GET/HEAD /health is the sole exception. This is a separate outer gate; Flask session, CSRF, memberships and assignments still authorize each application operation. The session response reports demo_mode for the factual demo notice. Production uses environment-managed secrets; no evaluator or application credential is built into the frontend.
