# Approved Lovable design to persisted application

The actual authorized reference project is `a0e42a3b-b921-4d20-bccf-70644b03c886` (QueueLess Pulse Design), revision `33d94a14a7936957eb1faaa09ef1aa085f1d7eb5`. Its component source was inspected read-only alongside the supplied screenshots. No change, publication or paid operation was made in Lovable.

| Reference | Production implementation | Real behavior / deliberate boundary |
| --- | --- | --- |
| `src/styles.css`, `shared.tsx` | `tokens.css`, `styles.css`, `components/layout.tsx`, `components/system.tsx` | Teal/navy tokens, brand, badges, KPI composition, compact role headers; no prototype role-switch toolbar or universal sidebar. |
| `shared.tsx` eye artwork | `components/eye-artwork.tsx` | Pure decorative SVG with unique instance IDs; no demo engine or metrics. |
| `patient.tsx` landing | `domains/customer/pages.tsx`, `service.tsx` | Actual business/service entry, waiting, availability and ETA; real CSRF-protected issuance. Generic services retain factual copy. |
| `patient.tsx` ticket | `domains/customer/ticket.tsx`, `recovery.tsx` | Actual private token, position, estimate, serving and recorded transitions; same-origin recovery, ownership and cancellation retained. Back returns to the existing active ticket rather than issuing again. |
| `doctor.tsx` | `domains/staff/doctor.tsx` | Assigned service and persisted duty; FIFO Call Next, existing COMPLETE for Mark Reviewed, Skip confirmation, audited same-token Recall and stale confirmation safeguards. Unsupported prototype source/recall-count fields are not invented. |
| `reception.tsx` | `domains/staff/reception.tsx` | Actual backend-generated scoped QR, download/print, permission-controlled walk-in and real slip; live waiting/current call. No decorative QR, made-up arrivals count or unauthorized Pause Arrivals control. |
| `owner.tsx` | `domains/owner/pages.tsx`, `operations.tsx`, `history.tsx`, `management.tsx` | Four accessible sections, real hourly operational data and business-local reviews/history, existing administration/export/audit. No fabricated feedback stars or synthetic chart constants. |
| `display.tsx` | `domains/display/page.tsx` | Dedicated public kiosk, actual called token/waiting/counter, reconnect/fullscreen/sound controls; no private recovery data. |

## Preserved authority

The Flask/SQLAlchemy/PostgreSQL backend remains authoritative. Navigation never grants a role. Reception uses its business-scoped permissions and explicit Owner walk-in grant; Doctor actions require active service assignments; Owner is tenant-scoped. Anonymous users may only enter public patient/display flows and their own private tickets. Session authentication, CSRF, rate limiting, queue locks, idempotency receipts and audit transitions remain enforced server-side.

The change adds no dependency or migration. Migration 005 from the preserved `691f2cf` product baseline remains required when a separately approved release moves beyond hosted `2844df3`; no hosted migration, reseed or deployment occurred here.

Interrupted patient joins keep their original request key across reloads and retries until the server confirms that issuance. An old completed-ticket snapshot cannot replace an unresolved key. The explicit Recover interrupted join action may reopen the original completed ticket before a fresh visit; it deliberately confirms an unknown outcome instead of silently creating another token. Real late-commit and lost-response browser tests verify this recovery path and subsequent fresh visits.

## Review evidence boundary

Functional acceptance uses real disposable PostgreSQL test schemas. Read-only preview screenshots use the preserved 15-ticket/34-event local fixture; its original date is not rewritten. Empty new-date statistics are factual. Android-size browser acceptance verifies this frontend. Native source and signed APKs are unchanged; the existing APK still loads hosted `2844df3` until a separately approved deployment, so it is not evidence of this reconstructed UI running in the hosted WebView.
