"""Capture CBP's current border wait snapshot into raw.cbp_snapshot.

CBP's feed only exposes the current state, so this job *is* the history:
each run stores the full response untouched. Identical responses are stored
once (SHA-256 of the canonical JSON).
"""
import hashlib
import json
import logging

from psycopg.types.json import Jsonb

from pipeline.db import connect, ensure_schema
from pipeline.http import get_json
from pipeline.run_log import logged_run

CBP_URL = "https://bwt.cbp.gov/api/bwtnew"
REQUIRED_KEYS = {"port_number", "port_name", "crossing_name", "border", "commercial_vehicle_lanes"}
LANE_KEYS = {"update_time", "operational_status", "delay_minutes", "lanes_open"}

log = logging.getLogger(__name__)


class SchemaError(ValueError):
    """The source changed shape; fail loudly rather than store junk."""


def validate(payload) -> None:
    if not isinstance(payload, list) or not payload:
        raise SchemaError("expected a non-empty JSON array")
    for record in payload:
        missing = REQUIRED_KEYS - record.keys()
        if missing:
            raise SchemaError(f"record {record.get('port_number')} missing {sorted(missing)}")
        cv = record["commercial_vehicle_lanes"]
        for lane in ("standard_lanes", "FAST_lanes"):
            if lane in cv and not LANE_KEYS <= cv[lane].keys():
                raise SchemaError(f"{record['port_number']} {lane} missing {sorted(LANE_KEYS - cv[lane].keys())}")


def payload_hash(payload) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def store_snapshot(conn, payload) -> int:
    """Insert the snapshot; returns 1 if stored, 0 if an identical one exists."""
    validate(payload)
    with conn.transaction():
        cur = conn.execute(
            "INSERT INTO raw.cbp_snapshot (payload_sha256, record_count, payload) "
            "VALUES (%s, %s, %s) ON CONFLICT (payload_sha256) DO NOTHING",
            (payload_hash(payload), len(payload), Jsonb(payload)),
        )
        return cur.rowcount


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with connect() as conn:
        ensure_schema(conn)
        with logged_run(conn, "ingest_cbp") as run:
            payload = get_json(CBP_URL)
            run.rows_loaded = store_snapshot(conn, payload)
            run.detail = f"{len(payload)} crossings" + ("" if run.rows_loaded else " (duplicate payload, skipped)")
            log.info("CBP: %s", run.detail)


if __name__ == "__main__":
    main()
