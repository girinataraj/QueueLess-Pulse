-- Additive only: does not change identities, queue state or existing audit history.
CREATE TABLE IF NOT EXISTS rate_limit_buckets (
    key_hash varchar(64) NOT NULL,
    window_start bigint NOT NULL,
    hits integer NOT NULL CHECK (hits > 0),
    PRIMARY KEY (key_hash, window_start)
);
CREATE INDEX IF NOT EXISTS ix_rate_limit_buckets_window_start ON rate_limit_buckets(window_start);
