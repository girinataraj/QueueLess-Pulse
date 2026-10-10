-- PostgreSQL only. Back up first. Execute in one transaction in a maintenance window.
-- Original timestamps were UTC values stored without timezone.
-- SET LOCAL app.business_timezone = 'Asia/Kolkata' before this script to override.
LOCK TABLE services, tickets, ticket_events IN ACCESS EXCLUSIVE MODE;
ALTER TABLE services ADD COLUMN seq_date date;
ALTER TABLE services ADD COLUMN last_number integer NOT NULL DEFAULT 0;
ALTER TABLE tickets ADD COLUMN business_date date;
ALTER TABLE tickets ADD COLUMN request_key varchar(36);
ALTER TABLE tickets ADD COLUMN owner_id varchar(36);
ALTER TABLE tickets ALTER COLUMN created_at TYPE timestamptz USING created_at AT TIME ZONE 'UTC';
ALTER TABLE ticket_events ALTER COLUMN timestamp TYPE timestamptz USING timestamp AT TIME ZONE 'UTC';
UPDATE tickets SET business_date = (created_at AT TIME ZONE COALESCE(NULLIF(current_setting('app.business_timezone', true), ''), 'Asia/Kolkata'))::date,
    request_key = token, owner_id = token;
-- Migrated ownership cannot be recovered from the former application; cancellation remains staff-managed.
ALTER TABLE tickets ALTER COLUMN business_date SET NOT NULL;
ALTER TABLE tickets ALTER COLUMN request_key SET NOT NULL;
ALTER TABLE tickets ALTER COLUMN owner_id SET NOT NULL;
ALTER TABLE tickets ADD CONSTRAINT uq_ticket_request_key UNIQUE(request_key);
ALTER TABLE tickets ADD CONSTRAINT uq_ticket_daily UNIQUE(service_id, business_date, daily_number);
ALTER TABLE tickets ADD CONSTRAINT ck_ticket_number CHECK(daily_number > 0);
ALTER TABLE tickets ADD CONSTRAINT ck_ticket_status CHECK(status IN ('WAITING','CALLED','COMPLETED','SKIPPED','CANCELLED'));
CREATE UNIQUE INDEX uq_one_called_service ON tickets(service_id) WHERE status = 'CALLED';
CREATE INDEX ix_ticket_queue ON tickets(service_id, status, id);
UPDATE services s SET seq_date = q.day, last_number = q.num FROM
    (SELECT service_id, business_date AS day, max(daily_number) AS num FROM tickets GROUP BY service_id,business_date) q
    WHERE q.service_id = s.id AND q.day = (SELECT max(business_date) FROM tickets WHERE service_id = s.id);
-- Any pre-existing duplicate daily numbers / active tickets abort the transaction; never silently rewrite history.
