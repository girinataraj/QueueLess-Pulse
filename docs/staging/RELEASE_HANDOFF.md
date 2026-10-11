# Separate staging and Android release handoff

This candidate starts from verified integration `efc36175ea994915adec75c5867d420f7e7b5104` on branch `codex/industry-grade-staging-apk`. It preserves Flask sessions, CSRF, SQLAlchemy/PostgreSQL transactions, service assignments, FIFO ordering, tenant authorization and audit transitions. Receptionist access remains separate from Owner privileges; Mark Reviewed remains COMPLETE.

## What changed

- Failed supplied gateway credentials are throttled by atomic PostgreSQL buckets shared across workers. Missing credentials receive the normal Basic challenge without consuming the password-guessing budget. Successful invitations do not grant an application role.
- Production responses have a Content Security Policy, per-response nonces for legacy inline scripts, HSTS and restrictive Permissions Policy. Staging requires a separate named PostgreSQL database, encrypted database transport, an exact public HTTPS origin and a distinct secure session cookie.
- Staging startup verifies the connected database and takes an advisory lock before additive schema creation. Legacy or mismatched databases fail closed. Startup never inserts accounts or seed tickets and never resets tables.
- Capacitor Android packaging uses no production credentials, cleartext exceptions, arbitrary backend selector or privileged native bridge for remote content. Only the configured HTTPS origin can navigate inside the app; certificate errors are cancelled. The gateway prompts privately. QR exports use scoped authenticated PNG endpoints without redirect following or storage permissions. Print QR opens Android's print framework. These connected native flows still require acceptance against the approved staging endpoint.
- Capacitor tooling's transitive UUID dependency is pinned to the patched CJS-compatible version for GHSA-w5hq-g745-h8pq; its identifier-generation API is tested. No advisory exclusions or lint baselines were added.
- The resolved native runtime Maven packages are exported and queried against OSV, including pagination. Missing audit responses fail the gate. Python, frontend and mobile tooling dependencies are also audited.

## Preserved fallback

The integrated fallback remains in `C:\Users\girin\.codex\worktrees\erode-monday-integration\DR`, on `efc36175`, served at http://127.0.0.1:5001/app/. Its isolated PostgreSQL database remains `127.0.0.1:55434 / queueless_erode_integration`. The older fallback and its `127.0.0.1:55433 / queueless_erode_demo` cluster are separate.

Private integrated credentials: `C:\Users\girin\.codex\worktrees\erode-monday-integration\DR\.tmp\PRIVATE_LOCAL_DEMO_ACCESS.md`. Reception-only access is in the adjacent `PRIVATE_RECEPTION_ACCESS.md`. Do not distribute the Owner or Doctor password with a patient QR.

Local links:

- Reception: http://127.0.0.1:5001/app/staff/reception
- Patient: http://127.0.0.1:5001/app/b/erode-eye-clinic-demo/service/1
- Doctor: http://127.0.0.1:5001/app/staff/login
- Owner: http://127.0.0.1:5001/app/owner/login
- Display: http://127.0.0.1:5001/app/b/erode-eye-clinic-demo/display

Restart the unchanged integrated fallback:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\girin\.codex\worktrees\erode-monday-integration\DR\scripts\start-local-demo.ps1' -Action restart -Port 5001
```

No Monday refresh has been executed. Use the existing integration's backup-first, date-guarded refresh documentation on October 12 in Asia/Kolkata; never import this fixture into a hosted database. Outstanding called tickets must be completed or skipped before Call Next. Existing history must remain intact.

## Verify this candidate locally

```powershell
Set-Location 'C:\Users\girin\.codex\worktrees\erode-staging-apk\DR'
npx.cmd --yes pnpm@11.25.0 --dir frontend install --frozen-lockfile --strict-peer-dependencies
npx.cmd --yes pnpm@11.25.0 --dir mobile install --frozen-lockfile --strict-peer-dependencies
& 'E:\Internship\New folder\DR\.venv\Scripts\python.exe' scripts\verify_staging_candidate.py --connection-profile 'C:\Users\girin\.codex\worktrees\erode-monday-integration\DR\.tmp\local-demo-private.json'
& 'E:\Internship\New folder\DR\.venv\Scripts\python.exe' -m pip_audit --format json --output evidence\python-advisories.json
& 'E:\Internship\New folder\DR\.venv\Scripts\python.exe' scripts\verify_secrets.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\build-android.ps1 -Variant Verification
```

The gate selects ONLY `queueless_erode_integration_test` and creates disposable schemas with freshly generated accounts. It never starts a cluster, writes the demo's public schema or uses inherited Render credentials. Browser screenshots mask private recovery links. Exact results are in ignored `evidence/candidate-gate.json`, JUnit reports and `evidence/RELEASE_VERIFICATION.md`.

The final local gate passed 147 Python tests, 14 frontend tests, 3 mobile tooling tests, 5 Android native policy tests and 3 Android emulator tests: **172 passed, 0 failed, 0 skipped**. Two additional full desktop/mobile workflows passed over trusted localhost HTTPS with production CSP and secure session cookies. No certificate-warning bypass or disabled TLS verification was used. The 50 resolved Android runtime Maven packages had no known OSV advisories at the scan time. Android lint had zero errors; its remaining template/resource/tool-version warnings are recorded in the lint report.

Android prerequisites: Node 24, pnpm 11.25.0, Java 21 and Android SDK 36. The installed SDK is `C:\Android`. Signing keys/passwords are protected in `.tmp\android-signing`; retain a private backup to sign future evaluation updates. APKs, signing keys, SDK configuration and build outputs are excluded from Git.

The generated `evidence\android\QueueLess-Pulse-Verification.apk` is an actual signed, non-debuggable installable Android package. It explicitly displays that staging is awaiting approval. It contains no live queue, embedded credentials or substitute mock data. It is **not the connected staging APK**.

## Deployment approval required

The budget is strictly **$0 / INR 0**. No card, paid plan, paid disk, paid preview, upgrade or billable add-on is authorized. No staging URL exists yet. The historical paid `render.staging.yaml` is **withdrawn and must not be applied**. The review-only `render.free-staging.yaml` proposes exactly one NEW Render Free web service, `queueless-pulse-staging-free`, with automatic deployments off, no Render database and no disk. Validation now checks this free-only proposal. It does not reference the protected hosted demo or its database.

The workspace's free Render PostgreSQL slot is occupied. A **new separate Neon Free project** is the proposed database alternative, subject to explicit provider/project approval. No project has been created and no application database has been switched. The full quotas, safeguards and connection requirements are in [ZERO_COST_STAGING.md](ZERO_COST_STAGING.md).

After separate explicit approval for the free resources and deployment:

1. Require the feature PR's backend/PostgreSQL/security and Android checks to pass. Deploy its verified commit directly; do not merge main. Linux Gunicorn verification remains in CI.
2. Recheck the Render workspace's included usage, no-card status and Neon Free account eligibility. Stop if a card or paid option is required. Create only the new approved Neon Free project, preferably PostgreSQL 18 in Singapore, and the new Free web service. Confirm the actual database name and role are isolated from every protected demo. Use the direct TLS connection, not the transaction-pooler endpoint. Supply a fresh gateway username and separate strong gateway/session secrets through environment management; never copy localhost/hosted credentials.
3. Set PUBLIC_BASE_URL to the actual assigned HTTPS origin and TRUSTED_HOSTS to that hostname alone. Build reproducible React assets with `scripts/render-build.sh`; launch using `scripts/start-staging.sh` (Gunicorn two workers, four threads, safe access logs).
4. Check managed TLS, health, gateway rejection/valid access, secure session cookies, CSRF, assets/SPA routing and forwarded-IP throttling. Register a fresh staging Owner privately behind the gateway; create exactly one fictional hospital, Main Reception, Eye Consultation, a Receptionist role and an active assigned Doctor using real authorized workflows. Any synthetic population must be explicitly scoped to this new database; do not copy passwords or recovery tokens from protected demos.
5. Verify Reception QR decoding/download/print, patient issuance/ETA, live updates, FIFO/Complete/Skip, Owner business-local reviews/history, unassigned staff denial and second-tenant isolation using synthetic records. Capture sanitized evidence.
6. Build the connected APK only after the real staging origin passes:

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\build-android.ps1 -Variant Staging -StagingOrigin 'https://ACTUAL-APPROVED-STAGING-HOST'
   ```

7. Verify the signed APK on Android against staging, including the gateway challenge, application role login, secure context, ticket creation/live updates and native QR printing/export. Physical-phone/hotspot testing remains deferred until separately resumed.

Rollback means selecting a previously verified staging commit and checking schema compatibility; never deleting/resetting databases. Preserve database backups before migrations. Neither the existing hosted demo nor GitHub main participates in this deployment path.

## Remaining release limits

Free-resource/provider approval, final remote CI, live HTTPS verification and connected APK acceptance are required. No paid deployment is an alternative under this budget. Do not announce the new deployment as live or the connected APK as verified before those steps pass.

Only invited technical evaluators and synthetic data are authorized. A formal operator, privacy contact, approved retention policy and legally reviewed terms/privacy policy remain unresolved. Existing draft legal documentation is retained. No claim of legal approval, real-patient readiness or unrestricted commercial release is made.
