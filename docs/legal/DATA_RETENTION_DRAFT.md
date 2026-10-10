# DRAFT — Actual storage and retention decisions

Status: engineering inventory, not an approved retention policy. No formal retention period or deletion schedule exists for application records. Synthetic demonstration data only is authorized.

| Record | Current actual behavior | Decision still needed |
| --- | --- | --- |
| Owner/staff username, optional email, password hash | Persists; identity/membership can be disabled, which is not deletion | Account lifetime, request handling, deletion/export and recovery |
| Business/branch/service configuration | Persists; branches/services can stop new joins; history remains | Retention after business closure and historical references |
| Tickets/recovery identifiers/browser ownership | Persist in PostgreSQL; completion/skipping/cancellation changes state without deleting the ticket | Ticket retention, private-link lifetime and anonymization rules |
| Ticket/admin audit events | Preserved; no application purge or tamper-proof database-admin guarantee | Audit period, access/erasure balance and archival controls |
| Invitation hashes | Acceptance blocked after 24 hours or first use; rows are retained | Row cleanup and audit preservation policy |
| Rate-limit counters | HMAC identifier, window and bounded counter; rows older than one hour are deleted when a subsequent limited request runs | Operational scheduling and provider storage/backups |
| Browser sessions | Signed cookie; identity/CSRF rotate on authentication, logout clears the session; loss removes cancellation authority | Any additional session expiration policy |
| Browser cache | Worker allowlist contains only public CSS and two icons; API/HTML are network-only | Physical device/update validation after deployment |
| Application/provider logs | Prepared Gunicorn access log omits URLs/query/auth; database errors log class; provider retention unconfirmed | Provider log retention, access and incident process |
| PostgreSQL backups/exports | No app-managed backup/deletion process; provider plan must be confirmed | Backup retention, restore drills, account ownership and deletion propagation |

No unattended deletion of accounts, tickets or audit history is implemented. Invitation expiry and logout are access changes, not record deletion. Closing the demo or deleting a hosting database is a separate authorized operation; no destructive operation is part of this release preparation. A future approved purge must account for foreign keys, immutable audit requirements, backups and recovery links, and must be tested with synthetic data before use.

Before any real-data launch, confirm the operator, privacy contact, jurisdictions, retention periods, deletion/export ownership, request verification, backup handling and incident contacts. Keep general commercial use and unrestricted real-customer registration blocked until those decisions are approved.
