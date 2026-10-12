# Product candidate verification and release

## Recoverable checkpoints

The candidate is on `codex/hospital-design-workflows`, based on application-auth release `2844df3e58503d8722c5eb18f3877d43249de5c9`.

* A — `9865aa4`: semantic design tokens, shared components, role navigation and responsive shell; 22 frontend tests passed.
* B — `8dbc45a`: Doctor duty/recall, shared issuance, explicit reception grant and additive operational schema; 53 selected backend tests passed.
* C/D — Reception/Patient, Owner/Display and desktop/mobile acceptance. Final evidence is recorded in the private handoff rather than storing accounts or ticket recovery links in Git.
* E — strict frontend production checks, full PostgreSQL regression suite, native tests/lint, signed APK and read-only HTTPS emulator navigation.

Before/after screenshots cover all five experiences at 1440, 1366, 768, 390 and 360 pixels. Automated axe checks target WCAG A/AA tags through 2.2; they are not a compliance certification. Browser acceptance exercises QR decoding, walk-in and patient issuance, recall, skip, break/resume, completion, live display and Owner reviews using isolated PostgreSQL schemas. Printing checks use actual print media with the browser print dialog stubbed; physical printers were not tested.

## Reproduce the gate

Use a disposable PostgreSQL test database with a name ending `_test`. `TEST_DATABASE_URL` must never reference a hosted demo or real customer database. Existing fixtures create/drop only unique owned test schemas. Keep the URL in an ignored private environment file; do not log credentials.

```sh
python -m pip install -r requirements-test.txt pip-audit==2.10.1
python -m playwright install chromium
pnpm --dir frontend install --frozen-lockfile --strict-peer-dependencies
python scripts/generate_contracts.py --check
pnpm --dir frontend run typecheck
pnpm --dir frontend run lint
pnpm --dir frontend run test
pnpm --dir frontend run build
python -m pytest -q --junitxml=evidence/ci.xml
python scripts/verify_secrets.py
python -m pip_audit
pnpm --dir frontend audit --audit-level=low
pnpm --dir mobile install --frozen-lockfile --strict-peer-dependencies
pnpm --dir mobile test
pnpm --dir mobile audit --audit-level=low
pnpm --dir mobile run sync
cd mobile/android
./gradlew testVerificationDebugUnitTest lintStagingRelease assembleStagingRelease exportRuntimeDependencies
```

A connected release build requires the existing ignored signing profile and verified HTTPS origin; see the existing Android release instructions. CI uses an installation-verification flavor and never needs private signing secrets. Python/frontend minimum gates are raised to 180/26; no security step is removed. New branch CI is pending publication and must not be described as green until its actual remote checks complete.

## Additive schema and approval-gated deployment

Migration `migrations/005_operational_workflows.sql` adds reception_grants, doctor_duties and operation_receipts. It does not rewrite tickets, delete history, seed accounts, grant walk-in privileges or change ticket statuses. Applying it twice on disposable PostgreSQL was verified to preserve existing ticket identities/statuses/request keys.

Before a separately approved release, take a database backup with the operator's existing authorized backup procedure and verify its restore on an isolated database. Record the approved commit, exact database identity and row counts. Do not run preview seeding or local helpers against Neon. Run `flask --app app upgrade-db` to inspect the plan, and `flask --app app upgrade-db --apply` only against the explicitly approved database. The staging startup initializer also creates missing additive model tables under an advisory lock; it never inserts demonstration tickets or accounts.

The existing Render Free service, Neon Free database, PR #4 and GitHub main remain unchanged during development. Any new branch publication must establish account-included zero-cost CI allowance first. Merging or redeploying requires explicit user approval. Reuse the existing Free plans without additional resources, upgrades or payment methods. Preserve application-session authentication, HTTPS secure cookies, CSRF, rate limits, host/origin restrictions and closed Owner registration.

After an approved deploy, verify the actual commit, health/schema, anonymous patient/display, protected role APIs, QR issuance and full synthetic workflow before claiming hosted feature parity. Use new synthetic test tickets only; no reset. If acceptance fails, redeploy verified `2844df3e58503d8722c5eb18f3877d43249de5c9`. Additive operational tables may remain; do not drop them or erase newer audit events to roll back the application.

## Android boundary

The signed product-review APK targets the existing HTTPS staging origin, pins navigation, keeps TLS verification, disables mixed content/debugging, retains screen-capture protection and adds no permissions. Android Back closes a dialog or follows WebView history before exiting; initial verification-screen history is cleared after successful HTTPS loading.

Because redeployment is approval-gated, the APK currently loads the previously deployed 2844 web UI. Local redesigned token tracking is verified at Android-size browser widths; redesigned native hosted workflows remain pending approval and hosted acceptance. Emulator navigation is read-only and does not issue Neon tickets. Physical Android testing is deferred. The existing signed application-auth APK remains the fallback. Do not label this a deployed redesigned Android release yet.

## Local preview

`scripts/start-product-preview.ps1` uses an explicit ignored profile, dedicated PostgreSQL 18 data directory and loopback database `127.0.0.1:55436/queueless_product_demo`. It rejects inherited/hosted database configuration and creates no schemas or seed data. Restart affects only the new product-preview process. Port 5002 and a separate session-cookie name preserve the port-5000/5001 fallbacks.

The private handoff contains absolute one-command restart instructions, account file, local URLs, screenshots, actual test totals and APK SHA-256. Keep it and signing files out of Git.
