# Product and workflow audit

Starting revision: `2844df3e58503d8722c5eb18f3877d43249de5c9`. Worktree: `queueless-role-experience`; branch: `codex/hospital-design-workflows`. Existing staging, Neon, localhost fallbacks and signed APK remain outside this development environment.

## Existing strengths

One transactional ticket engine, service locks, a partial unique CALLED constraint, FIFO ordering, server-side service assignments, tenant membership guards, CSRF, shared database rate limits and audit history already exist. Patient recovery is a private capability link. Anonymous Patient and Public Display are deliberately public; staff roles use sessions. Reception already has real scoped QR images and live counts. Today's Reviews already filters by the completion date in the business timezone.

## Findings and implementation order

1. **Shared foundation:** CSS combines entire components in long declarations with repeated literal colors. Called and completed use the same visual state. Sidebar shows all roles, and mobile converts it to a horizontal scroller. Establish semantic tokens, consistent cards/buttons/forms, a focused sidebar, mobile dialog navigation, explicit breadcrumbs and reusable operational components.
2. **Doctor operations:** Call, Skip and Complete work, but duty/break/end/recall are absent. The active token competes with summary cards; elapsed time and personal activity are missing. Persist availability independently of ticket status. Recall must append an event to the same CALLED ticket. Break/end must reject an unresolved call. Keep one service lock and explicit assignment checks.
3. **Reception / Patient:** Reception cannot see the FIFO list or issue a walk-in token. An explicit owner-granted walk-in capability is necessary; a read-only membership must not implicitly acquire issuance permissions. Reuse issuance, not a second engine. Public-number lookup must be scoped to service/date and omit recovery IDs. Patient needs clear availability, progress and reconnection states; private recovery must never be the default share target.
4. **Owner / Display:** Preserve existing management controls but separate live and historical measurements. Add actual today-issued, duration/wait samples, hourly arrivals/completions and duty visibility. Display should prioritize distance-readable tokens, selection and public reconnection feedback.
5. **Verification / Android:** Capture all five real interfaces at 1440, 1366, 768, 390 and 360 pixels. Run the baseline plus operational security/concurrency/date tests, axe, keyboard and responsive acceptance. The native application loads the deployed HTTPS UI: new web behavior cannot be claimed hosted until a separately approved deployment.

## Operational boundaries

This is anonymous queue management, not an EMR or triage system. No identities, medical notes or emergency priority rules are introduced. No configured opening hours currently exist; “open” means enabled in queue configuration. Reception cancellation assistance remains outside scope because the existing cancellation authority belongs to the issuing patient browser. Optional audible alerts require a user gesture and are foreground-only.

## Evidence

Before/after captures and executable reports are in the ignored private product-review evidence directory. Screenshots use a new PostgreSQL 18 loopback cluster, fictional records and separate credentials. No staging database is used for UI development.
