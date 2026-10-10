# Restricted evaluator release runbook

Authorized scope: privately invited technical evaluators/project reviewers/testers; fictional businesses and synthetic queue/account data only. **Not legally approved or production-ready for real customers.** No destructive data operations, seed imports or publicly distributed credentials.

## Current release blockers

1. The feature PR must pass both push and pull_request checks at its final head, and the user must approve merging that concrete PR. No automatic merge is authorized.
2. Confirm the account-owned Render workspace and PostgreSQL choice/region/plan. The connected account exposes `giri's workspace`; confirmation is pending. The blueprint deliberately takes DATABASE_URL as a private environment input, so it does not create an unintended database or spend money.
3. Configure the real HTTPS origin, allowed hostnames and strong private secrets, initialize a **fresh empty** database (or back up/review an additive upgrade of an intended existing database), then pass hosted health and four-role/isolation tests. No live URL or provider startup is claimed before those checks.
4. Validate the actual Render proxy chain and forwarded-header spoof resistance before distributing evaluator access. The prepared rate limiter trusts one appended hop; adjust only against verified edge behavior. HTTPS is provided by Render's edge and must be verified on the actual service.

Missing operator/privacy contact/reviewed terms/retention are blockers for unrestricted/real-data/commercial launch, not for the authorized restricted synthetic demonstration. Draft privacy/terms/storage documents are in docs/legal. Backup/restore, monitoring/incident ownership, user recovery/export/deletion and approved retention must be established before broader real-world use. Physical-device installation and wider load testing are additional unverified operations.

## Reproducible configuration

| Setting | Prepared value / action |
| --- | --- |
| Service | Private GitHub repo girinataraj/QueueLess-Pulse, root DR application, branch main only after approved merge |
| Runtime/build | Python 3.12.14, Node 24.19.0, pinned pnpm 11.25.0; `bash scripts/render-build.sh` |
| Frontend | Frozen lockfile, strict peer dependencies, contract drift check, strict TS and Vite build; assets served at /app/assets, deep-link fallback under /app only |
| Start | `gunicorn --workers 2 --threads 4 --bind 0.0.0.0:$PORT --access-logfile - --access-logformat 'method=%(m)s status=%(s)s duration_us=%(D)s' --error-logfile - app:app` |
| Deploy trigger | `off`; explicit approval and manual deployment |
| Health | /health checks database/schema, including limiter table; no private record data; GET/HEAD bypass evaluator gate |
| APP_ENV | production; rejects SQLite and absent/short environment SECRET_KEY, forces secure cookies and no debug |
| SECRET_KEY | Generated strong secret in hosting environment, never source/chat/logs |
| DATABASE_URL | Account-owned PostgreSQL only; private environment setting; TLS for external connections |
| DEMO_MODE | true; protects both original/React UI, APIs, assets and registration |
| DEMO_ACCESS_USER | Environment-provided reviewer name, not an application owner identity |
| DEMO_ACCESS_PASSWORD | Generated private secret at least 32 characters; share only privately with invited reviewers |
| PUBLIC_BASE_URL | Actual https:// service origin; canonical QR/invite generation |
| TRUSTED_HOSTS | Verified service hostname plus any required loopback health hostname; do not accept arbitrary origins |
| BUSINESS_TIMEZONE | Asia/Kolkata default/legacy context; each business owns an IANA timezone |
| Limits | Auth 30 POST attempts / 300 seconds; queue issue 120 POST attempts / 60 seconds; shared legacy/React groups, database-atomic across workers |
| Proxy trust | RATE_LIMIT_TRUSTED_PROXY_HOPS=1 in Render blueprint, 0 locally; validate actual edge chain |

Render schema validation has passed against the official current JSON Schema. The validation initially caught an unquoted YAML `off` parsed as boolean; the configuration now quotes the string. The build performs **no database mutation**. There is no default account or development seed. Generated dist/node_modules are excluded from Git; hosting builds from locked source.

## Earliest safe deployment path after approval

1. Inspect the PR, exact reports and green checks. Obtain explicit user approval to merge. Merge, synchronize main and verify its workflow before hosting the same revision.
2. Use the confirmed user-owned Render workspace. Create/select the approved PostgreSQL resource in the same region; inspect account availability/limits. Obtain its connection settings privately through the account, never chat/report/Git. A free database is suitable only for the bounded demo and has provider expiry/backup limits; no durable production promise is made.
3. Initialize the intended new empty database with `python -m flask --app app initdb` using environment-managed production settings. This creates schema only. For an existing database, take a backup and review `python -m flask --app app upgrade-db --apply`; migration 004 only adds the limiter table/index. Do not point commands at an unspecified database, run drop/reset, copy a preview database or run seed.py.
4. Configure the Python web service with the prepared build/start/health commands and secrets. Set the exact HTTPS origin and trusted hosts. Keep DEMO_MODE=true and auto-deploy off. A first deployment with no schema must remain unhealthy until deliberate initialization is complete.
5. Inspect complete build/start logs; verify frontend asset building and Gunicorn workers. Check HTTPS redirect/certificate, `/health` and unauthenticated access denial for both UIs/API/registration. Validate the real proxy chain without logging raw secrets. Verify Secure/HttpOnly/SameSite cookies and no debug.
6. With private evaluator authorization, register generated synthetic owner/staff identities, create two fictional businesses, branches/services and assignments; issue a synthetic customer ticket from a separate browser, call/complete/skip/cancel as appropriate and observe customer/display/owner updates. Verify cross-business owner reads/mutations and staff unauthorized service actions are denied. Decode real scoped QR links against the HTTPS origin. Check browser refresh/deep links, mobile layout, PWA cache privacy and network recovery.
7. Confirm persistence across an authorized service restart using those synthetic records. Record the final commit/service URL/test evidence without account passwords, database URLs or ticket/invitation bearer URLs. Share only the HTTPS URL and privately provisioned reviewer access. Announce a **restricted demo live** only after hosted workflows pass. Do not describe it as a real-customer production launch.

## References checked during preparation

[Render native runtimes/tools/HTTPS](https://render.com/docs/native-runtimes), [Python version](https://render.com/docs/python-version), [Blueprint schema](https://render.com/schema/render.yaml.json), [manual deployment lifecycle](https://render.com/docs/deploys), [free hosting/database limits](https://render.com/docs/free). Free PostgreSQL currently expires after 30 days and free compute does not have provider logical backups; verify the actual selected plan before use. These provider constraints do not define this application's legal data-retention policy.

## Rollback

Original Jinja routes/QRs remain intact and receive the same outer demo access control. The new API reuses existing transaction handlers; no queue model/history is replaced. Roll back frontend release/revision or route reviewers to the original interface only with an explicit decision; do not silently substitute the old UI for a failed React gate. Additive limiter schema can remain when rolling back code; removing it is not necessary and is not part of this runbook.
