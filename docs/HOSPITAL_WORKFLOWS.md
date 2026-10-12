# Single-hospital product workflows

This feature branch starts at verified application-auth revision `2844df3e58503d8722c5eb18f3877d43249de5c9`. It uses fictional Erode Eye Clinic — DEMO, Main Reception and Eye Consultation. No names, diagnoses, clinical notes, priority scores or medical information are collected. This is queue management, not an EMR, triage system or legally approved real-patient release.

## Roles and operational authority

| Experience | Actual implemented behavior | Authority |
| --- | --- | --- |
| Reception | Scoped QR display/download/print, FIFO waiting list, currently called token, today's reviewed/skipped counts, estimates, doctor availability, service/date token lookup, desk activity | Active business membership permits reception reads. Walk-in issuance additionally requires an explicit Owner grant. It never grants Owner administration or consultation actions. |
| Patient | Anonymous join, digital token, actual position/estimate, live status/timeline, refresh recovery, cancellation, foreground call notification, optional sound/vibration, explicitly revealed private recovery link, share public queue entry | Existing patient-browser ownership and private capability link. Reception-issued slips contain no recovery token. Cancellation stays patient-owned. |
| Doctor | Assigned queue, start duty, call FIFO next, recall same called token, Skip confirmation, Mark Reviewed, break/resume/end, actual elapsed time, today's duration samples and own ticket activity | Existing server-side service assignment and active membership. Owner queue authority remains compatible with the previous release. |
| Owner | Real live/today KPIs, Today's Reviews, business-local date-filtered history, hourly arrivals/completions, observed waits/durations, service comparison, event-attributed workload, duty and administration audit, minimal CSV | Owner membership for the requested business, CSRF on mutations and audited exports. Management, activation, assignments and service configuration remain available. |
| Public Display | Distance-readable current token, counter, waiting count, service selection, fullscreen, reconnect feedback, optional foreground sound and reduced-motion announcement | Anonymous, explicitly public data only. Announcement versions are opaque; recovery tokens and identities are excluded. |

## Doctor responsibilities and deterministic actions

Duty is persisted independently from ticket status as AVAILABLE, ON_BREAK or OFF_DUTY. Existing ticket states remain WAITING, CALLED, COMPLETED, SKIPPED and CANCELLED. Mark Reviewed invokes the existing COMPLETE transition. Recall records RECALLED on the same CALLED ticket; it neither issues a token nor advances FIFO.

All operational mutations serialize on the existing service row lock and recheck authority. The PostgreSQL one-CALLED-per-service constraint remains intact. Break and End Duty reject any unresolved CALLED ticket. Complete or Skip it first. Concurrent Call Next and Break have one serialized outcome: either a call succeeds and break is rejected, or break succeeds and call is rejected. Skipping confirms the captured ticket, so a polling update cannot silently retarget the action.

Duty and recall use actor-bound UUID submission receipts. Reception walk-ins use the same transactional issuance function as anonymous patients, with an explicit capability, rate limits, CSRF, scoped receipt and audit event. Reception receives only a public number/date, never patient browser ownership or a recovery capability. The grant is not automatically assigned by migrations.

For compatibility, existing accounts without a duty record retain prior queue behavior until duty is explicitly started. Membership, account and assignment revocation exclude a duty record from advertised availability.

## Dates, estimates and measured analytics

Today's terminal counts use finished timestamps in the business timezone, not token issue dates. A previous-day ticket completed today appears in Today's Reviews. The dedicated page fixes today's finished-date and COMPLETED filter even if conflicting query parameters are supplied. History retains explicit date, issue/finish basis, service and terminal-state filters.

Daily numbering changes at the business-local midnight. Outstanding older WAITING/CALLED tickets remain intact and FIFO retains their order. Equal public numbers on different dates are disambiguated by service and issue date. An unresolved CALLED ticket is never silently cleared on rollover.

Arrival estimates use queue length multiplied by configured service duration. They are approximations, not appointments. Consultation/wait analytics use persisted timestamps with displayed sample counts; missing samples show an em dash. Workload attributes the completion/skip event to the account that recorded it. Live operational counts are visually separate from all-recorded historical analytics.

## Recovery, privacy and current limitations

Private ticket links are capability credentials: keep them private. The default share action shares the service-entry URL. Public displays and minimal slips never include recovery IDs. CSV exports contain public synthetic token number, dates, service ID and terminal status, use formula-safe token values and append REPORT_EXPORTED. Export requires a standard browser; the Android client intentionally permits scoped QR downloads only.

Availability is an observed duty/configuration indicator, not a staffing guarantee. Configurable operating hours, long-queue alert policies, reception-assisted cancellation, translations, background push and clinical priority rules are not implemented. Sound and vibration require a foreground user gesture and platform support. Data persists until an authorized administrative process changes it; no automatic deletion or retention period is promised.

The synthetic-only legal restrictions and closed staging Owner registration remain in force. No new HTTP Basic challenge, authentication bypass, clinical data collection or hosted-database reset is introduced.
