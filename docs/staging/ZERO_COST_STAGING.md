# Zero-cost staging proposal — approval pending

Budget: **INR 0 / USD 0**. This document prepares a restricted synthetic-data staging release; it does not authorize creation, deployment, a main merge or provider changes. Reviewed baseline `3c5226d57ec96ea7dab8f9979dbf68ef0cf0d55e` remains in Git history. The localhost fallback and existing hosted release/database must remain unchanged. The historical paid Blueprint is withdrawn.

## Verified billing safeguards on October 11, 2026

Authenticated GitHub billing showed 44 of 3,000 included Actions minutes used, 0 of 2 GB included artifact storage used, and $0 net Actions charges before publication. Its existing Actions budget was $0 with **Stop usage: Yes**. No billing setting was changed. Private branch publication and standard Ubuntu CI therefore fit the included allowance with paid usage blocked. Check current usage again before additional runs; do not weaken tests or select larger/paid runners. PR #4 is https://github.com/girinataraj/QueueLess-Pulse/pull/4.

Authenticated Render billing for **giri's workspace** showed Hobby, **no card on file**, $0 current/projected charges, 0.55 of 750 free instance hours used, 10 MB of 5 GB bandwidth used and 4 of 500 pipeline minutes used. Remaining allowances at inspection were 749.45 hours, about 4.99 GB and 496 minutes. These are workspace-wide, not dedicated to the new service. The existing service remains Free with automatic deployments disabled. No resources or billing controls were changed.

Render documents that without a payment method, bandwidth exhaustion suspends Free services and build-minute exhaustion blocks new builds rather than billing. Free-hour exhaustion suspends **all** workspace Free web services. A new staging service can therefore affect the protected demo's availability if shared quotas are exhausted. Recheck headroom before provisioning and monitor it during the short demonstration; close polling dashboards when finished. Do not run synthetic keep-alives or upgrade to restore service. [Render Free limits](https://render.com/docs/free).

## Separate resources proposed

| Resource | Plan and configuration | Cost |
| --- | --- | --- |
| Render `queueless-pulse-staging-free` | Free web service, Singapore, one instance, managed HTTPS, auto-deploy off, no disk/previews | $0 within included limits |
| Neon `queueless-pulse-erode-staging` | New Free project, PostgreSQL 18 if confirmed in Console, Singapore where available, one branch, fixed 0.25 CU with scale-to-zero | $0; never upgrade |
| Database `queueless_pulse_staging` | New dedicated database and application role, no copied credentials/data | Included in new Neon Free project |

Neon's current public Free plan requires no credit card and includes 100 projects, 10 branches per project, 1 GB PostgreSQL storage per project (20 GB account total), 100 CU-hours per project/month and 5 GB outbound transfer per project/month. At 0.25 CU, 100 CU-hours gives at most 400 active hours. Scale-to-zero after five minutes is mandatory. Instant restore is limited to six hours or 1 GB of changes; one manual snapshot and one day of monitoring are included. Actual account eligibility/project/storage headroom still needs verification after project approval. Do not enable Neon Auth, Functions, Object Storage, AI Gateway, read replicas, paid backups or other unrelated products. [Current pricing](https://neon.com/pricing), [plans and hard limits](https://neon.com/docs/introduction/plans), [October 2 storage update](https://neon.com/blog/neon-free-plan-1-gb-per-project).

Neon Free suspends compute on compute/transfer exhaustion; storage-increasing operations fail at the storage cap. No automatic upgrade is authorized. Keep a private local PostgreSQL dump before any data migration; do not rely on the short restore window as a full backup policy.

## Flask/PostgreSQL compatibility

Use a **direct**, non-`-pooler` Neon hostname over TCP 5432. Schema startup uses a session-level advisory lock; Neon's PgBouncer transaction mode does not support that lock. The existing SQLAlchemy/psycopg2 client, row locking, transactions, audit writes and shared database rate limits remain unchanged. `pool_pre_ping` is already enabled for reconnections after idle suspension. Default SQLAlchemy pools for two workers allow up to 30 application connections; verify the actual `SHOW max_connections` result after creation. Use only this new project's credentials. [Pooling compatibility](https://neon.com/docs/connect/connection-pooling), [SQLAlchemy guide](https://neon.com/docs/guides/sqlalchemy).

Keep TLS enabled (`sslmode=require`, with channel binding where supported). Staging enforces encrypted database transport and the explicit `STAGING_DATABASE_NAME=queueless_pulse_staging`. Verify `current_database()`, current role, server version and TLS before schema creation; never log the connection URL/password. No connection to Neon has been attempted because project/provider approval is pending.

Render Free can make outbound connections to an external PostgreSQL database. Render may suspend Free services for unusually high service-initiated public traffic, including external database traffic; its threshold is not published. This remains an availability risk to verify under the actual synthetic workload. Free web services sleep after 15 minutes without incoming traffic and can take approximately one minute to start. Neon can also sleep. Open the service before the presentation, without artificial keep-alives. Persist records in Neon, never in Render's ephemeral filesystem or SQLite. Free hosting is suitable for this invited demo, not a claimed production SLA.

## Deployment and APK procedure after approval

1. Confirm PR #4 checks are green at the exact selected head commit. Recheck all no-card/free quotas. Obtain approval for both the new Neon Free provider/project and new Render Free service/deployment. No main merge is required.
2. Create only the specified new project/database/role. Choose Free explicitly and stop at any payment requirement. Store new database and gateway credentials in protected ignored local files/environment management; no secrets in GitHub or the APK.
3. Use `render.free-staging.yaml` or its equivalent Dashboard settings. Keep `plan: free`, auto-deploy off, no disk, no previews and no Render database. Set the exact actual assigned `https://...onrender.com` origin as `PUBLIC_BASE_URL`, that hostname alone as `TRUSTED_HOSTS`, a fresh generated `SECRET_KEY`, `DEMO_MODE=true`, fresh restricted gateway credentials and the new direct TLS `DATABASE_URL`. The actual assigned URL is unknown until provisioning; no placeholder is a working endpoint.
4. Build with `bash scripts/render-build.sh`; start with `bash scripts/start-staging.sh`. Startup validates the isolated database and performs only additive schema creation under an advisory lock. Check `/health`, managed HTTPS, secure cookies, CSP, CSRF, SPA routing, gateway and proxy-aware throttling. Register fresh staging accounts behind the gateway and configure one fictional hospital, Main Reception and Eye Consultation with Receptionist and actively assigned Doctor roles. Do not import protected demo accounts or recovery tokens. Any synthetic seed must be separately verified against this new database identity.
5. Verify Reception QR download/print/decode, Patient issuance/ETA/live status, Doctor FIFO/Skip/Complete, Public Display, Owner local-date reviews/history and unauthorized/second-tenant isolation. Capture sanitized evidence. Do not announce a live release before these pass.
6. Build a connected signed APK using the actual verified HTTPS origin:

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\build-android.ps1 -Variant Staging -StagingOrigin 'https://ACTUAL-VERIFIED-STAGING-HOST'
   ```

7. Verify the APK against the deployed origin on Android: trusted TLS, restricted gateway, role login, Patient token/live updates and native scoped QR export/printing. Do not bypass TLS, embed passwords, use localhost/hotspot addresses or mislabel the existing installation-verification APK as connected. Retain signing material privately in `.tmp\android-signing`.

A connected APK is technically feasible before Monday morning if free-provider eligibility, approval, deployment and hosted acceptance succeed promptly. Reserve approximately two to three active hours after approval for provisioning, full hosted workflows, connected build and Android verification; this is an estimate, not a guarantee. The signed verification APK already exists, but there is no connected staging URL/APK yet.

Only invited technical evaluators and synthetic data are authorized. Formal operator, privacy contact, approved retention and legal terms remain unresolved. The free proposal does not remove those launch restrictions.
