# Testing Report — QueueLess Pulse Universal Edition

Verified 2026-10-10, Asia/Kolkata. Authoritative root: `E:\Internship\New folder\DR`; `QueueLess_MVP` remains untouched.

## Final executed result

**73 passed, 0 failed, 0 skipped in 131.45 seconds.** Authoritative evidence: `evidence/universal-final.xml` and `evidence/universal-final.log`. JUnit records 73 cases, zero errors/failures/skips, elapsed 131.451 seconds. Original 34 scenarios remain and passed. Pre-change baseline actually ran: 34 passed in 58.16 seconds (`universal-baseline.xml/.log`).

| Category | Cases | Result |
| --- | ---: | --- |
| Original unit/configuration/CLI | 22 | Passed |
| Universal functional/security | 34 | Passed |
| Real PostgreSQL integration | 13 | Passed |
| Desktop/mobile Playwright | 4 | Passed |
| Total | 73 | 0 failed, 0 skipped |

Environment: Python 3.12.14, PostgreSQL 18.6, Windows, headless Microsoft Edge with Playwright 1.63.0. Versions: `universal-environment.txt`. Compilation and `pip check` passed. Final pip-audit: **No known vulnerabilities found** (`universal-dependency-audit.json/.log`). This is published-advisory coverage, not proof of absence of every vulnerability.

## Verified workflows and completion gate

- Customer: business/branch/service selection, downloaded QR decoded and actual URL visited, anonymous issuance, daily uniqueness, duplicate replay, private recovery/browser history, serving token/position/ETA, authorized cancellation and all five states.
- Staff: secure login/logout, scoped membership/assignment, waiting lists, live updates, FIFO call/complete/skip, one active ticket, revoked permissions, error/empty states.
- Owner: registration/authentication, business/branch/service management and activation, staff creation, expiring one-use invitations, assignments/revoke, QR downloads, live statistics, actual timing, throughput and completed/skipped history.
- Public Display: business/branch scope, serving token/service/counter, refresh/full-screen/reconnection, no private identifiers.
- Isolation: foreign URLs/payloads denied; staff/public data scoped; PostgreSQL rejects cross-business assignments; old invitations cannot restore revoked membership.
- PostgreSQL: issuance/duplicate/call/finish races, stable row lock blocking, independent queues, revocation serialization, unique/one-active constraints, migration preservation and atomic conflict rollback.
- Production-like PostgreSQL startup/health, secure cookies, missing-secret/SQLite rejection passed.
- Desktop/mobile PWA: manifests, worker registration, static-only cache and responsive workflows passed. Hosted install prompts/physical Android installation await deployment.

No known critical defect remains in the verified scope. Hosting is paused for local UI inspection at the user's request.

## Scenario map

| Source | Coverage |
| --- | --- |
| tests/test_app.py | Health/rendering, CSRF/auth, uniqueness/replay, FIFO/ETA/events/states, cancellation, midnight rollover, invalid inputs, database constraints/private caching |
| tests/test_config.py | Production rejection, timezone boundary, called-ticket cancellation, bootstrap/private CLI provisioning |
| tests/test_postgres.py | Two batches of eight concurrent issuances, four concurrent calls, complete vs skip, independent queues, duplicate replay, held service lock, completion vs call, valid/conflicting legacy migrations, production smoke |
| tests/test_universal.py | Owner/business/branch/service/team; foreign URL/payload denial; revoke/invites; metrics/history/audit; validation/QR/CSRF; inactive queue draining; no default credentials; three PostgreSQL isolation/constraint/upgrade cases |
| tests/test_browser.py | Original customer/staff/display lifecycle, desktop/mobile, network loss/restore, cache |
| tests/test_universal_browser.py | Owner creates business/branch/service/team, QR decode/navigation, customer join, staff call/complete, customer/display/owner updates, metrics/history/PWA; 1366x900 and 390x844 |

PostgreSQL tests use separate connections/clients and random schemas inside isolated loopback `queueless_test`, verifying committed state after races. No production database was accessed. Migration tests preserve representative IDs/tokens/events/timestamp instants and verify complete rollback on conflicting history, plus upgrade of the previous audited schema. These are bounded integration checks, not load/distributed-outage certification.

## Exact final execution commands

```powershell
Set-Location -LiteralPath 'E:\Internship\New folder\DR'
$env:TEMP=(Resolve-Path .tmp).Path
$env:TMP=$env:TEMP
$env:TEST_DATABASE_URL='postgresql+psycopg2://queueless_test@127.0.0.1:55439/queueless_test'
$env:PLAYWRIGHT_EXECUTABLE_PATH='C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
& .\.venv\Scripts\python.exe -m compileall -q app.py models.py config.py access.py universal.py tests
& .\.venv\Scripts\python.exe -m pytest -q --junitxml=evidence/universal-final.xml *> evidence\universal-final.log
& .\.venv\Scripts\python.exe -m pip check
& .\.venv\Scripts\python.exe -m pip_audit --format json --output evidence\universal-dependency-audit.json
```

Installed PostgreSQL binaries initialized ignored `.tmp/pgdata` on loopback port 55439. Trust authentication is only for this disposable test cluster. Without TEST_DATABASE_URL the 13 PostgreSQL cases intentionally skip; the final run had zero skips. CI is prepared in `.github/workflows/verify.yml` but has not executed on GitHub.

## Failures fixed and retested

The Universal focused run exposed duplicate-prefix handling returning 503: audit creation triggered premature autoflush. Audit staging now uses `no_autoflush`; constraint conflicts return 409 with rollback. Retained evidence: `universal-duplicate-failure.xml`. Focused retest passed 31 cases with one PostgreSQL case excluded. Expanded PostgreSQL passed 13; browser passed four. Final integration then passed all 73 without exclusions/skips.

`evidence/previous-testing-report.md` preserves the earlier audit's driver, timestamp-assertion, template-encoding failures and retests. Earlier `final.xml/.log` records the prior 34-case version; **universal-final.xml/.log supersedes it**. No coverage percentage is claimed.

## Screenshots and limits

`evidence/universal-{owner,customer,staff,display}-{1366,390}.png` records all four actual browser experiences. Mobile owner overview and staff/display evidence were visually inspected. QR images were decoded in browser verification. All screenshots are local.

No known failing test or unfinished requested MVP workflow remains. Invitations are manually shared links, not email delivery. Ticket viewing uses an unguessable bearer URL; cancellation requires the issuing signed session. Losing that session loses cancellation authority. SQLite preview is single-process; legacy SQLite migration is not automated. Login throttling/password reset, backups/monitoring, abuse protection, cloud outage/load testing, APK/push and multi-counter operation are outside verified MVP scope. Gunicorn Linux launch, hosted HTTPS flows, cloud restart durability and physical-device installation remain deployment-stage checks.

## Exact local UI preview commands

Use the existing venv and a separate SQLite preview database:

The preview initialization command was executed successfully. A startup smoke check returned HTTP 200 for `/health`, `/owner/register`, `/staff/login`, `/` and `/display`. This additional check is separate from the 73-test suite. The isolated PostgreSQL test server was shut down after verification. Only report/README changes followed the final suite; no application behavior changed.

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

Open `/owner/register`, create your owner/business/branch/service, then create staff and assign permissions. Separate browser profiles let owner, staff and customer remain signed in independently. Customer `/`, staff `/staff/login`, owner `/owner`, display `/display`; scoped links are in the owner dashboard. No default credentials are created. Keep the same terminal open to retain its secret. Ctrl+C stops preview. Generating another secret invalidates old sessions but preserves data.
