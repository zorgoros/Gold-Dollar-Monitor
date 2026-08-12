-- V1 schema (ARCHITECTURE.md §10). Timestamps are UTC ISO-8601 text.

CREATE TABLE instruments (
    id             INTEGER PRIMARY KEY,
    symbol         TEXT    NOT NULL UNIQUE,
    name_fa        TEXT    NOT NULL,
    asset_class    TEXT    NOT NULL,
    canonical_unit TEXT    NOT NULL,
    active         INTEGER NOT NULL DEFAULT 1,
    metadata_json  TEXT    NOT NULL DEFAULT '{}'
);

INSERT INTO instruments (symbol, name_fa, asset_class, canonical_unit) VALUES
    ('usd_irr_free', 'دلار آزاد',      'currency', 'toman/usd'),
    ('gold_18k',     'طلای ۱۸ عیار',   'gold',     'toman/gram'),
    ('xau_usd',      'انس جهانی طلا',  'gold',     'usd/troy_oz'),
    ('emami_coin',   'سکه امامی',      'coin',     'toman/coin');

-- Raw observations. Append-only: nothing in the service updates a row here.
CREATE TABLE quotes (
    id               INTEGER PRIMARY KEY,
    instrument_id    INTEGER NOT NULL REFERENCES instruments(id),
    provider         TEXT    NOT NULL,
    provider_symbol  TEXT    NOT NULL,
    raw_value        TEXT    NOT NULL,
    normalized_value REAL    NOT NULL,
    currency         TEXT    NOT NULL,
    unit             TEXT    NOT NULL,
    source_timestamp TEXT,
    retrieved_at     TEXT    NOT NULL,
    quality_status   TEXT    NOT NULL,
    raw_payload_hash TEXT    NOT NULL DEFAULT '',
    metadata_json    TEXT    NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_quotes_instrument_time ON quotes(instrument_id, retrieved_at);

CREATE TABLE snapshots (
    id          INTEGER PRIMARY KEY,
    snapshot_at TEXT NOT NULL,
    status      TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE INDEX idx_snapshots_time ON snapshots(snapshot_at);

CREATE TABLE snapshot_quotes (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
    quote_id    INTEGER NOT NULL REFERENCES quotes(id),
    PRIMARY KEY (snapshot_id, quote_id)
);

-- The analytical time series: raw instrument values and derived values both land
-- here, so a trend lookup has one query path instead of two.
CREATE TABLE metrics (
    id            INTEGER PRIMARY KEY,
    snapshot_id   INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
    metric_name   TEXT    NOT NULL,
    metric_value  REAL    NOT NULL,
    unit          TEXT    NOT NULL,
    model_version TEXT    NOT NULL,
    created_at    TEXT    NOT NULL
);
CREATE INDEX idx_metrics_name_time ON metrics(metric_name, created_at);

CREATE TABLE signals (
    id                INTEGER PRIMARY KEY,
    snapshot_id       INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
    instrument        TEXT    NOT NULL,
    classification    TEXT    NOT NULL,
    severity          INTEGER NOT NULL,
    confidence        REAL    NOT NULL,
    summary_fa        TEXT    NOT NULL,
    reason_codes_json TEXT    NOT NULL,
    model_version     TEXT    NOT NULL,
    created_at        TEXT    NOT NULL
);

CREATE TABLE reports (
    id                  INTEGER PRIMARY KEY,
    snapshot_id         INTEGER REFERENCES snapshots(id),
    report_type         TEXT    NOT NULL,
    report_key          TEXT    NOT NULL,
    content             TEXT    NOT NULL,
    channel             TEXT    NOT NULL,
    generated_at        TEXT    NOT NULL,
    sent_at             TEXT,
    delivery_status     TEXT    NOT NULL,
    telegram_message_id INTEGER,
    model_version       TEXT    NOT NULL
);

-- The idempotency guard: one delivered report per key, enforced by the database
-- rather than by a check the scheduler could race.
CREATE UNIQUE INDEX idx_reports_delivered_key
    ON reports(report_key) WHERE delivery_status = 'SENT';

CREATE TABLE job_runs (
    id            INTEGER PRIMARY KEY,
    job_name      TEXT NOT NULL,
    started_at    TEXT NOT NULL,
    finished_at   TEXT,
    status        TEXT NOT NULL,
    error_type    TEXT,
    error_message TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_job_runs_name_time ON job_runs(job_name, started_at);
