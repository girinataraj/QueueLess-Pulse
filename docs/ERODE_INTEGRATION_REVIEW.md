# Antigravity integration review and local verification

## Source and isolation

Reviewed Antigravity's committed `feat/erode-reception-ui` at `530858e66f167694cd706b93d8477d6c96d1eeab`, including its actual nine-file diff and `handoff.md`. Imported that commit only into `tmp/erode-monday-integration`, based on the verified fallback snapshot `761545b` (approved application baseline `f895908340c589d1730b061de964d1fe63323783`). The import had no textual conflicts.

Original Antigravity and fallback worktrees are preserved. The original root's uncommitted preview changes, Android files, private files and earlier backup are untouched. In particular, the uncommitted restricted-gateway deletion in the original root was not imported. GitHub main remains at `f895908`; no push, merge or deployment is authorized or performed here.

The candidate has its own localhost server at port 5001 and a freshly created, separately verified PostgreSQL 18 cluster at **127.0.0.1:55434 / queueless_erode_integration**. The fallback remains at port 5000 with **127.0.0.1:55433 / queueless_erode_demo**. The candidate has a distinct session cookie name and separate PostgreSQL roles/passwords. Application demo accounts were copied privately so existing Owner/Doctor/Reception access remains familiar.

## Verified integration defects and fixes

1. **Missing QR endpoint.** Antigravity's image referenced `/api/v1/staff/services/<id>/qr.png`, absent from the committed backend. Implemented actual scoped PNG generation by sharing the existing QR rendering helper, with authenticated active-business membership checks, download headers, service-specific entry URLs and a print layout. Foreign/revoked memberships cannot obtain QR images.
2. **Reception depended on clinical assignments.** The page queried `/staff/queues`, which correctly excludes an unassigned Reception account. Assigning services would grant clinical mutations. Added a separate read-only `/reception/queues` API for active business members; Reception stays unassigned and cannot administer the business or call, complete or skip tickets. Existing clinical service-assignment checks remain unchanged.
3. **Broken generated contracts/build.** Antigravity manually edited generated TypeScript without updating the strict JSON Schema, and the analytics test fixture lacked the new required fields. Reproduced TypeScript TS2739. Updated the source schema, regenerated TypeScript, fixed the fixture, and kept strict response contract validation.
4. **Wrong day for carried-over reviews.** Issue-date counts omitted an older CALLED ticket completed today. Counts and Today's Reviews now use actual finish timestamps bounded by the business timezone, while ticket issue dates and event history remain intact. Added both issue-date and finish-date history filters, strict date validation, server-authoritative today, DST boundary tests and Sunday-to-Monday PostgreSQL regressions.
5. **Print was only a download link.** Added separate Download QR and Print QR actions, with a QR-focused print stylesheet and real-browser decoding/print-layout assertions.
6. **Incomplete Owner view/error handling.** Today's Reviews now lists only completed consultations, shows actual totals and business-local date, handles loading/errors and links to the full audit. History has date and date-basis controls. The browser acceptance uses the controls and verifies the completed ticket's audit events.
7. **Mobile keyboard accessibility.** The extended acceptance found a scrollable history table without keyboard focus access. Added focusable labelled table regions and retained all axe checks. Also fixed a browser-test race that navigated away before Reception authentication completed; this did not require changing authentication.

The Doctor label Mark Reviewed still invokes the original COMPLETE handler. FIFO ordering, one active ticket, SQLAlchemy models, PostgreSQL locks, CSRF, RBAC, rate limiting and the restricted gateway are preserved. No new application dependencies or schema migrations were needed.

## Records, refresh and backup evidence

Copied all original 15 tickets and 34 ticket events into the separate candidate. Before current-day preparation, made a private custom-format PostgreSQL backup. The explicit refresh completed six older outstanding tickets through normal Doctor calls/completions and added 15 new daily fixture tickets. No old ticket/event was deleted or backdated.

Current candidate: **30 tickets**, with **5 waiting, 1 CALLED, 20 completed and 4 skipped** across history. For Sunday October 11, **13 completed today and 2 skipped today** are factual: six carry-over completions plus seven new fixture completions. The new fixture itself is 7 completed / 2 skipped / 1 called / 5 waiting. The already-called daily E010 must be resolved before Call Next.

The fallback's original 15 ticket rows and 34 event rows match sealed SHA-256 snapshots exactly, and its real Owner/Doctor logins were checked again. Actual restoration of the refresh backup into a new disposable test database recovered all original 15 tickets and 34 events with matching hashes. Evidence: ignored `evidence/fallback-preservation.json` and `evidence/backup-restore-verification.json`.

Monday preparation is explicit and repeatable; see `MONDAY_ERODE_HANDOFF.md`. It refuses future/backdated dates, current-day unrelated records, missing backups and simultaneous refresh commands. Repeating a completed daily refresh does not reset or duplicate data. Unit and PostgreSQL tests verify retained identities/events, failure safety, carry-over completion dates and idempotence.

## Verification evidence

Final gate on October 11: **116 Python/backend/browser tests passed, 0 failed, 0 skipped**; **14 frontend tests passed, 0 failed, 0 skipped**. Total: **130 passed, 0 failed, 0 skipped**. All 98 baseline tests are included, plus 15 new authorization/date/refresh cases and 3 populated-demo browser cases. Strict TypeScript, ESLint, production React build, generated contract check, Python compile checks, Python/frontend dependency audits and Gitleaks staged/index/all-history scans passed. No test, scanner rule or workflow was disabled. No remote CI run was triggered because nothing was pushed.

The complete gate runs `scripts/verify_erode_local.py`. Final counts and status are recorded in ignored `evidence/final-gate.json`, with full JUnit in `evidence/complete.xml` and frontend JUnit in `evidence/frontend.xml`. Required checks include strict TypeScript, ESLint, production build, API schema generation, all baseline/new Python tests, PostgreSQL concurrency/isolation, desktop/mobile browser flows, dependency audits and unmodified Gitleaks rules against the staged application and all Git history. No skipped tests are accepted by the gate.

The running persisted candidate additionally passed **10 read-only desktop/mobile interface checks and 2 print-layout checks**, with **zero axe violations and zero horizontal overflow**. Its real service QR decoded to `http://127.0.0.1:5001/app/b/erode-eye-clinic-demo/service/1`. Ticket/event snapshots stayed unchanged. Evidence: `evidence/live-preview-verification.json`, with `live-*.png` screenshots. Physical Android, hotspot/HTTPS setup, APK and cloud work are deferred by user instruction, not failed.
