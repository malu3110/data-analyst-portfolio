"""Load BTS monthly inbound truck crossings by port into raw.bts_truck_crossing.

Full refresh: BTS revises recent months, and the whole Trucks series is small
(tens of thousands of rows), so replace-all in one transaction is simplest and
always consistent.
"""
import logging

from pipeline.db import connect, ensure_schema
from pipeline.http import get_json
from pipeline.run_log import logged_run

BTS_URL = "https://data.bts.gov/resource/keg4-3bc2.json"
PAGE_SIZE = 50_000
COLUMNS = ("port_code", "port_name", "state", "border", "date", "measure", "value")

log = logging.getLogger(__name__)


def fetch_trucks(since: str = "2015-01-01") -> list[dict]:
    rows, offset = [], 0
    while True:
        page = get_json(BTS_URL, params={
            "$select": ",".join(COLUMNS),
            "$where": f"measure='Trucks' AND date >= '{since}'",
            "$order": "date, port_code",
            "$limit": PAGE_SIZE,
            "$offset": offset,
        }, timeout=120)
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        offset += PAGE_SIZE


def replace_rows(conn, rows: list[dict]) -> int:
    if not rows:
        raise ValueError("BTS returned no rows; refusing to truncate existing data")
    missing = {"port_code", "date", "measure"} - rows[0].keys()
    if missing:
        raise ValueError(f"BTS rows missing {sorted(missing)}")
    with conn.transaction():
        conn.execute("TRUNCATE raw.bts_truck_crossing")
        with conn.cursor() as cur:
            with cur.copy(
                "COPY raw.bts_truck_crossing (port_code, port_name, state, border, month, measure, value) FROM STDIN"
            ) as copy:
                for r in rows:
                    copy.write_row([r.get(c) for c in COLUMNS])
    return len(rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with connect() as conn:
        ensure_schema(conn)
        with logged_run(conn, "ingest_bts") as run:
            run.rows_loaded = replace_rows(conn, fetch_trucks())
            log.info("BTS: loaded %s rows", run.rows_loaded)


if __name__ == "__main__":
    main()
