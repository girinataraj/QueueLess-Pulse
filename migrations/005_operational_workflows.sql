-- Additive only: no ticket rewrite, status change, data deletion or privilege backfill.
CREATE TABLE IF NOT EXISTS reception_grants (
  membership_id INTEGER PRIMARY KEY REFERENCES memberships(id)
);
CREATE TABLE IF NOT EXISTS doctor_duties (
  id SERIAL PRIMARY KEY,
  service_id INTEGER NOT NULL REFERENCES services(id),
  staff_id INTEGER NOT NULL REFERENCES staff(id),
  state VARCHAR(12) NOT NULL CHECK (state IN ('AVAILABLE','ON_BREAK','OFF_DUTY')),
  started_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL,
  CONSTRAINT uq_doctor_duty UNIQUE(service_id, staff_id)
);
CREATE TABLE IF NOT EXISTS operation_receipts (
  id SERIAL PRIMARY KEY,
  service_id INTEGER NOT NULL REFERENCES services(id),
  staff_id INTEGER NOT NULL REFERENCES staff(id),
  request_key VARCHAR(36) NOT NULL,
  action VARCHAR(32) NOT NULL,
  ticket_id INTEGER REFERENCES tickets(id),
  timestamp TIMESTAMPTZ NOT NULL,
  CONSTRAINT uq_operation_request UNIQUE(staff_id, request_key)
);
