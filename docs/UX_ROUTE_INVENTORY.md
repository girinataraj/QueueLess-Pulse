# Route reconstruction: 691f2cf baseline

This audit covers every React route in app.tsx, the shared sidebar, public links and the five operational journeys. Implementation stays on codex/hospital-design-workflows. The preserved baseline is 691f2cfba8a4391159bc220439a85601965e89e2. No database or API changes are planned.

## Counting rule

Count a user-facing screen as a non-error route pattern that renders a page, including legitimate conditional selection or registration flows. Do not count modals, drawers, tabs, transient loading/error states or the catch-all. Before: 18 rendering route patterns. Target after: 13 rendering patterns plus five compatibility-only redirects. All 18 old URLs remain supported. Single-business/service selection routes resolve automatically with replace-navigation; multi-business/service selection remains meaningful and supported.

## Complete route inventory

| Current route (under /app) | User / current purpose | Decision | Final behavior / destination |
| --- | --- | --- | --- |
| / | Patient business directory | KEEP / simplify | One business resolves directly to its entry. Multiple businesses use compact real choices. No internal-role navigation. |
| /b/:slug | Patient branch selector | MERGE | All relevant services in one entry workspace; no extra branch-choice page. One service resolves directly. |
| /b/:slug/branch/:branchId | Patient branch entry | REDIRECT | /b/:slug?branch_id=:branchId; service scope preserved, invalid scope never widened. |
| /b/:slug/service/:serviceId | Patient service QR entry | KEEP | Clinic/service context, real queue/availability, primary Join Queue. No extra selection. |
| /ticket/:token | Patient private live ticket | KEEP | Token-centred mobile layout; ownership/recovery/cancellation retained. |
| /my-tickets | Patient browser ticket history | REDIRECT / MERGE | /?tickets=1 opens recovery drawer in patient workspace; history and saved-link recovery retained. |
| /staff/login | Doctor / Reception sign-in | KEEP | One shared login component; reception intent preserved by query. |
| /owner/login | Owner sign-in | KEEP | Shared form component with Owner destination. |
| /owner/register | Authorized Owner onboarding | KEEP | Existing configuration restriction; never enable registration. Closed state offers real existing-account login. |
| /invite/:token | Private team onboarding | KEEP | Existing authenticated/invited account acceptance, scoped permissions unchanged. |
| /staff/dashboard | Doctor service operations | KEEP | Focused consultation/duty console, no public/Owner navigation. |
| /staff/reception | Reception desk | KEEP | Queue/arrival actions and QR in context; no Owner/Doctor navigation. |
| /owner | Owner portfolio/create business | KEEP / conditional | One owned business opens directly. Explicit portfolio mode preserves creation and multi-business administration. |
| /owner/business/:businessId | Owner operations/admin | KEEP / consolidate | Accessible tabs include reviews/history; no duplicate standalone dashboards. |
| /owner/business/:businessId/reviews | Owner completed today | REDIRECT / MERGE | Same Owner workspace, section=reviews&review=today; business-local completion filter forced. |
| /owner/business/:businessId/history | Owner filtered audit history | REDIRECT / MERGE | Same workspace, section=reviews&review=history; date/service/status/page preserved. |
| /display | Display business chooser | REDIRECT / MERGE | /?view=display; one business opens kiosk, meaningful chooser only for multiple. |
| /b/:slug/display | Public live display | KEEP | Dedicated kiosk shell, only public queue data and display controls. |
| * | Unknown/obsolete entry | KEEP error handling (not counted) | Clear recovery link to public entry; no privileged redirect. |

## Navigation and actions

Remove the universal Patient/My Tickets/Staff/Reception/Owner/Display sidebar, decorative breadcrumbs, repeated slogans, generic footer and legacy-interface shortcut. Public patient navigation contains branding and useful private ticket recovery only. Internal login links remain valid direct URLs. Doctor and Reception each receive a compact workspace header and account controls; real display links remain scoped within Reception. Owner uses its existing accessible tabs and portfolio access, rather than another duplicate navigation layer. Display has a standalone full-height layout.

Preserve every backend operation: walk-in grant, shared issuance, QR download/print, slip print, private recovery, cancel ownership, duty, recall, stale confirmation, FIFO, complete/skip, audits, export, registration restrictions and all account/admin forms. Move duplicate Owner TodayHistory and standalone history into one reusable paginated review/history panel. Branch and business QR bookmarks resolve to usable service entry without broadening scope.

## Screen purpose / action / required information

| Screen family | Why / primary action | Information before acting | Consolidation / real-data / responsive check |
| --- | --- | --- | --- |
| Patient entry | Join the specified service | Clinic, location, availability, waiting and estimate | No branch step; live API; mobile first |
| Patient token | Follow turn, recover/cancel when permitted | Number, status, ahead, ETA, serving and timeline | Recovery drawer/tools in context; actual ticket; accessible |
| Shared login / invitation / eligible registration | Obtain authorized role access | Intended workspace and validation/error | Reused form, no role privileges inferred from navigation |
| Reception | Register arrival and show QR | Serving, waiting, availability, explicit permission | One desk, scoped real queue; desktop grid/mobile stacking |
| Doctor | Resolve current call or call FIFO next | Current token, elapsed, duty, assignment, wait list | One console with activity/confirmations; live backend |
| Owner portfolio (when needed) | Select/create business | Actual owned businesses | Single-business default bypass; creation retained explicitly |
| Owner operations | Review/manage actual hospital | Business-local KPIs, services, permissions, audit | Tabs/forms and unified paginated history; actual data |
| Display | Announce serving token | Large number, service/counter, wait and connection | Full-height kiosk; anonymous public-only payload |

## Verification plan

Meaningful navigation tests cover five redirects, query/scope preservation, direct QR, default single-service landing, Back and mobile recovery/navigation, role separation and protected APIs. Preserve existing lifecycle, duty, walk-in, Owner form and printing assertions. Capture actual functional states at 1440/1366/768/390/360 px in a separate BEFORE/AFTER review pack. Run the complete 180 Python + 26 frontend baseline and update totals only for added meaningful coverage. Native source/signing remain unchanged; reuse the unchanged APK/native evidence and clearly report its hosted-frontend boundary.
