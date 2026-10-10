# CI failure investigation - QueueLess Pulse

Date: 2026-10-10 (Asia/Kolkata). Published baseline: b131c5eda2f371374505af9e815fc1a6aa0d03ea.

## Actual failure evidence

[Run 38030196917, attempt 1](https://github.com/girinataraj/QueueLess-Pulse/actions/runs/38030196917/attempts/1) failed in `python -m pytest -q --junitxml=evidence/ci.xml`. The process exited **139: segmentation fault**, so no final JUnit was produced and the later audit step did not execute. PostgreSQL service, dependency installation, Chromium installation and compilation had succeeded. Complete original log was downloaded to ignored `.tmp/ci-original-failure.log`.

Runner: Ubuntu 24.04, Python 3.12.15, PostgreSQL 18.6. The fatal trace shows concurrent Werkzeug request threads inside SQLAlchemy result loading/current_user and QR authorization while the main thread runs Playwright. Attempt 2 on the unchanged commit passed 73 tests and the security audit; that establishes intermittency, not a repair.

## Underlying fixture defect and reproduction

The threaded browser server reused the single-thread unit fixture's `sqlite:///:memory:` database. Flask-SQLAlchemy selects StaticPool for this configuration. Two concurrently checked-out Connections were verified to return **the same DBAPI connection**. Polling/browser requests therefore execute concurrently on a single SQLite connection/transaction, an unsupported use of StaticPool. SQLAlchemy [documents this concurrency limitation](https://docs.sqlalchemy.org/en/21/dialects/sqlite.html#using-a-memory-database-in-multiple-threads-or-coroutines).

The new regression test fails deterministically against the original fixture at the independent-connection assertion (`evidence/ci-regression-before.xml`), then passes after the fix (`ci-regression-after.xml`). It also proves that one request's rollback cannot discard another connection's uncommitted work. The unsafe fixture condition is reproduced locally; the native segmentation fault itself was observed in Linux CI, not reproduced on Windows. A Python fatal trace cannot establish the exact native instruction that faulted without a core/native debugger.

## Narrow repair

- `tests/conftest.py`: keep in-memory SQLite for single-thread unit tests; introduce per-test file-backed SQLite for browser tests, sharing seed/cleanup code and disposing engines.
- `tests/test_browser.py`: use the browser fixture for the threaded server, close the server before fixture database cleanup, add the connection/transaction isolation regression.
- Documentation records this failure and its verification. Application code, authentication, tenant isolation, PostgreSQL locks/migrations and all original 73 test scenarios are unchanged.

No tests, security steps or workflow triggers are disabled. Workflow provisioned its isolated `_test` PostgreSQL database and dependencies correctly. Browser temporary databases are unique per test and excluded from Git. CI uses only throwaway test credentials, no production secrets. Linux verification uses the existing Ubuntu Actions workflow because Docker/WSL Linux execution is unavailable locally.

## Verification

Local full suite: **74 passed, 0 failed, 0 skipped in 153.196 seconds** (`evidence/ci-fix-local.xml/.log`). Compilation and pip check passed; dependency audit found no known vulnerabilities (`ci-fix-advisories.json/.log`). PR checks will be verified against the final fix commit. Original passing local result remains 73; the additional regression brings the fixed suite to 74. No merge or deployment is authorized by this investigation.
