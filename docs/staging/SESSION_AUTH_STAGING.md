# Application-session authentication for the new Free staging release

Status: feature candidate; redeployment requires explicit user approval. GitHub main, the original `queueless-pulse-demo` and all existing database records must remain unchanged. Do not apply this document to the original hosted demo or either localhost fallback.

The new staging candidate uses the existing Flask signed sessions and server-side role checks. Anonymous visitors can open the directory, scoped Eye Consultation QR destination, public display and their bearer ticket recovery links. Issuance remains CSRF protected, idempotent and rate limited. Public display responses contain only queue/service information, never recovery tokens or credentials. No customer identity/account is required.

Reception signs in at `/app/staff/login?experience=reception`, Doctor at `/app/staff/login`, and Owner at `/app/owner/login`. Active business memberships permit reception reads; clinical actions require service assignments (or existing Owner permission). Owner management/history remains business scoped. Anonymous privileged API requests return application errors without `WWW-Authenticate: Basic`.

Owner registration is disabled at the existing shared server handler, covering the API and legacy GET/POST routes. React hides new-owner invitations and provides an existing-account login on the registration route. CLI administration and authorized staff invitations retain their existing controls; no unrelated authentication architecture was introduced.

## Exact staging configuration after approval

Deploy the verified PR #4 feature commit to ONLY `queueless-pulse-staging-free`:

```text
APP_STAGE=staging
APP_ENV=production
DEMO_MODE=true
STAGING_AUTH_MODE=application
OWNER_REGISTRATION_ENABLED=false
```

Keep the existing strong `SECRET_KEY`, separate TLS `DATABASE_URL`, expected database name, exact public HTTPS origin/trusted host, proxy configuration and automatic-deploy OFF setting. Do not remove the old gateway password as a substitute for the mode change. Existing gateway secrets may remain unused for rollback. No secret is included in this document.

The mode is accepted only for explicitly isolated staging. Staging still requires production mode, HTTPS, strong secrets, TLS PostgreSQL and a distinct database; unrestricted owner registration is rejected. Default `basic` mode remains unchanged for the original evaluator demo. `DEMO_MODE` now describes synthetic-only operation; the session response separately reports actual `gateway_required` and `owner_registration_enabled` flags.

No schema migration, reset, reseed, deletion or direct modification of Neon records is necessary. Validate the deployed startup identity, anonymous responses and protected role APIs before any normal synthetic ticket walkthrough. Do not merge into main, provision resources or upgrade a plan.

## Android

The connected shell opens the scoped HTTPS patient page directly. Native invitation fields, dialog, credential caching/reuse and Basic download headers are removed. An unexpected HTTP authentication challenge is explicitly cancelled without prompting. Authorized QR downloads forward only the application's session cookie to the existing pinned-origin QR endpoint. TLS errors remain cancelled; origin pinning, no cleartext/mixed content, no privileged remote JS bridge, non-debug release and FLAG_SECURE are retained.

Two obsolete Basic-challenge policy cases are replaced by pinned patient-entry and invalid URL policy cases; the complete six-test native policy suite remains. An additional tooling check prohibits native credential collection/forwarding. Full hosted and connected-emulator workflow acceptance is pending the approved backend redeployment. The rebuilt candidate cannot operate against the old Basic-gated backend; preserve the prior working APK until acceptance passes.

## Verification and rollback

The backend retains all baseline tests and adds actual PostgreSQL/TLS session-mode, registration, anonymous-denial, ticket privacy, CSRF, rate-limit and role tests. Existing Basic-gateway regression tests remain for the original demo. Desktop/mobile-size fresh-browser cases add anonymous patient/display entry and normal Reception/Doctor/Owner logins. CI provisions TLS only inside its disposable PostgreSQL 18 service; no production credentials are used. Test count floors are increased, never lowered.

Before deployment verify green CI and a private data backup. After deployment require no Basic challenge on normal navigation/login, anonymous patient/display success, privileged denial, valid role login/permissions, real synthetic queue transitions, QR privacy and Android acceptance with ordinary certificate validation. Those normal acceptance actions add synthetic tickets/audit events; never reset or delete prior records.

If acceptance fails, stop release distribution and revert only this staging service to its saved backend revision `e4e49fb82a4080d3d0e9c2069ca2bb873889de16` with Basic gateway configuration. Preserve the existing Neon database/history and the previous APK. Main and the original hosted demo are not rollback targets.

This remains a synthetic demonstration for technical evaluation. Public QR access does not authorize real-patient processing or commercial launch. Operator identity, privacy contact, legally approved terms and retention decisions remain unresolved.
