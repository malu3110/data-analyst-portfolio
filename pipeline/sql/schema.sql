-- Raw layer: data exactly as received. All parsing happens downstream in dbt.
CREATE SCHEMA IF NOT EXISTS raw;

-- One row per distinct CBP response (the full JSON array, untouched).
CREATE TABLE IF NOT EXISTS raw.cbp_snapshot (
    snapshot_id     bigserial PRIMARY KEY,
    captured_at     timestamptz NOT NULL DEFAULT now(),
    payload_sha256  text        NOT NULL UNIQUE,
    record_count    integer     NOT NULL,
    payload         jsonb       NOT NULL
);

-- BTS monthly inbound truck crossings by port (full refresh each load).
CREATE TABLE IF NOT EXISTS raw.bts_truck_crossing (
    port_code   text NOT NULL,
    port_name   text,
    state       text,
    border      text,
    month       text NOT NULL,
    measure     text NOT NULL,
    value       text,
    loaded_at   timestamptz NOT NULL DEFAULT now()
);

-- Every pipeline run, successful or not, so gaps and failures are measurable.
CREATE TABLE IF NOT EXISTS raw.pipeline_run (
    run_id       bigserial PRIMARY KEY,
    job          text        NOT NULL,
    started_at   timestamptz NOT NULL DEFAULT now(),
    finished_at  timestamptz,
    status       text        NOT NULL DEFAULT 'running',
    rows_loaded  integer,
    detail       text
);
