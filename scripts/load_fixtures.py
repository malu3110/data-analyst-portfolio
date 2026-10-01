"""Load the captured real-source fixtures into DATABASE_URL (used by CI before dbt build)."""
import json
from pathlib import Path

from pipeline.db import connect, ensure_schema
from pipeline.ingest_bts import replace_rows
from pipeline.ingest_cbp import store_snapshot
from pipeline.run_log import logged_run

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

with connect() as conn:
    ensure_schema(conn)
    with logged_run(conn, "ingest_cbp") as run:
        run.rows_loaded = store_snapshot(conn, json.loads((FIXTURES / "cbp_snapshot.json").read_text()))
    with logged_run(conn, "ingest_bts") as run:
        run.rows_loaded = replace_rows(conn, json.loads((FIXTURES / "bts_trucks.json").read_text()))
print("fixtures loaded")
