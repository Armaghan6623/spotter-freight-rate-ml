-- Spotter freight-rate ML warehouse schema
-- Applied automatically on first Postgres container start.

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS ml;

-- Labeled development data (train_test.csv)
CREATE TABLE IF NOT EXISTS raw.train_test (
    id              BIGSERIAL PRIMARY KEY,
    load_id         TEXT,
    pickup          TEXT,
    delivery        TEXT,
    pickup_lat      DOUBLE PRECISION,
    pickup_lon      DOUBLE PRECISION,
    delivery_lat    DOUBLE PRECISION,
    delivery_lon    DOUBLE PRECISION,
    distance        DOUBLE PRECISION,
    equipment       TEXT,
    weight          DOUBLE PRECISION,
    date            DATE,
    market_index    DOUBLE PRECISION,
    quote_signal    DOUBLE PRECISION,
    rate            DOUBLE PRECISION,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 12,000 loads for final predictions
CREATE TABLE IF NOT EXISTS raw.validation (
    id              BIGSERIAL PRIMARY KEY,
    load_id         TEXT NOT NULL,
    pickup          TEXT,
    delivery        TEXT,
    pickup_lat      DOUBLE PRECISION,
    pickup_lon      DOUBLE PRECISION,
    delivery_lat    DOUBLE PRECISION,
    delivery_lon    DOUBLE PRECISION,
    distance        DOUBLE PRECISION,
    equipment       TEXT,
    weight          DOUBLE PRECISION,
    date            DATE,
    market_index    DOUBLE PRECISION,
    quote_signal    DOUBLE PRECISION,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_validation_load_id UNIQUE (load_id)
);

-- December chart lanes
CREATE TABLE IF NOT EXISTS raw.december_chart_inputs (
    id              BIGSERIAL PRIMARY KEY,
    pickup          TEXT,
    delivery        TEXT,
    distance        DOUBLE PRECISION,
    equipment       TEXT,
    weight          DOUBLE PRECISION,
    date            DATE,
    predicted_rate  DOUBLE PRECISION,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Submission template (load_id + predicted_rate)
CREATE TABLE IF NOT EXISTS raw.validation_predictions_template (
    id              BIGSERIAL PRIMARY KEY,
    load_id         TEXT NOT NULL,
    predicted_rate  DOUBLE PRECISION,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_template_load_id UNIQUE (load_id)
);

-- Model outputs land here later
CREATE TABLE IF NOT EXISTS ml.validation_predictions (
    id              BIGSERIAL PRIMARY KEY,
    load_id         TEXT NOT NULL,
    predicted_rate  DOUBLE PRECISION NOT NULL,
    model_version   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ml_pred_load_id UNIQUE (load_id)
);

CREATE INDEX IF NOT EXISTS idx_train_test_date ON raw.train_test (date);
CREATE INDEX IF NOT EXISTS idx_validation_date ON raw.validation (date);
CREATE INDEX IF NOT EXISTS idx_validation_equipment ON raw.validation (equipment);

-- Ingestion audit log
CREATE TABLE IF NOT EXISTS raw.ingestion_runs (
    id              BIGSERIAL PRIMARY KEY,
    dataset_name    TEXT NOT NULL,
    source_file     TEXT NOT NULL,
    row_count       INTEGER NOT NULL,
    status          TEXT NOT NULL,
    message         TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ
);
