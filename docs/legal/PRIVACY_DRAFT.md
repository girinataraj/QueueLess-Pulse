# DRAFT — Privacy notice for a restricted evaluator demonstration

Status: implementation-based draft for review, not legally approved. A formal operator, jurisdiction and privacy contact have not been confirmed. Do not represent the project name, GitHub username or an employer as a registered controller/company.

## Scope and permitted use

This demonstration is for technical evaluators, project reviewers and privately invited testers. Use fictional businesses, synthetic queue tickets and demo-only accounts. Do not enter real patient/customer data, sensitive business information or credentials used elsewhere. Unrestricted registration, real customer collection and general commercial use are launch-blocked.

## Information the implementation stores

Owner/staff identities include a username, optional email, password hash and active status. Business profiles contain name, category, description and IANA timezone; branches contain name/address; services contain configuration, counters and queue duration. Memberships and assignments determine access. Queue tickets record number, business date, status/timestamps, replay UUID, recovery token and a browser ownership identifier. Queue/admin events preserve operational audit history. Invitations store a token hash, creator, expiry and consumption time.

The signed HttpOnly session cookie carries the application identity/browser ownership and CSRF state. Production cookies use Secure and SameSite=Lax. The app does not request personal customer registration for ticket issuance. A recovery URL intentionally grants viewing of that one ticket; cancellation also requires its issuing browser session. Keep recovery and invitation URLs private.

Rate limiting stores a secret-key HMAC of the network identifier with a fixed window and counter, rather than the raw address. Expired counter rows older than approximately one hour are removed on subsequent limited requests. This is the limiter's actual cleanup behavior, not a retention promise for account/queue data. Application polling requires network access. The worker caches only public CSS/icons, never confidential API responses or HTML.

## Intended purpose and visibility

Data supports the synthetic demonstration's queue operation, access checks, approximate waits, operational metrics and audit history. Owners see their business management/history; staff see active assigned queues; customer ticket views require bearer recovery URLs. Reception feeds expose service/branch/counter/current number/waiting count without customer ownership identifiers or private ticket tokens. The outer evaluator access gate does not replace these role checks.

## Hosting and logging

Planned hosting is an account-owned Render web service with an account-owned PostgreSQL database. The deployment account, database provider/region, final URL, provider agreements and incident contacts must be confirmed before release. The prepared Gunicorn access-log format omits URLs, query strings and authorization headers; infrastructure providers may maintain their own connection/access logs. No claim is made about provider data location or log retention until verified in the actual account.

## Retention and requests

Accounts, configuration, tickets and audit events persist until an authorized database operation removes them. The application has no self-service export, account deletion, password reset or scheduled ticket/account purge. Invitation expiry prevents later acceptance but does not delete the row. See DATA_RETENTION_DRAFT.md. A request/contact process cannot be offered as established until a factual contact is designated.

## Unresolved before real customer launch

Operator/controller identity; applicable jurisdictions and lawful processing basis; privacy contact and rights/request process; approved retention/deletion/backups; processor agreements/data regions; incident response; any rules for minors or sensitive/health data; legally reviewed publication and consent/notice obligations. These fields remain unresolved. This draft does not certify GDPR, DPDP, HIPAA or other compliance.
