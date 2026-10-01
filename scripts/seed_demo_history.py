"""LOCAL DEVELOPMENT ONLY: fabricate a week of hourly CBP snapshots.

The real pipeline needs days of hourly captures before the hourly-profile and
FAST views have anything to show. To build and test those views locally, this
script takes the real captured snapshot (tests/fixtures/cbp_snapshot.json) and
generates synthetic waits for each hour of the past week.

The numbers it produces are invented. It refuses to run against anything but a
localhost database, so demo data can never reach the deployed database.
"""
import argparse
import copy
import hashlib
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from psycopg.types.json import Jsonb

from pipeline.db import connect, database_url, ensure_schema

FIXTURE = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "cbp_snapshot.json"
OFFSETS = {"PDT": -7, "MDT": -6, "CDT": -5, "EDT": -4, "EST": -5, "MST": -7}


def zone_for(record) -> str:
    for lane in ("standard_lanes", "FAST_lanes"):
        text = record["commercial_vehicle_lanes"].get(lane, {}).get("update_time", "")
        if text:
            return text.split()[-1]
    return "CDT" if record["border"] == "Mexican Border" else "EDT"


def lane(minutes: int | None, at_local: datetime, tz: str, status: str | None = None) -> dict:
    if minutes is None:
        return {"update_time": "", "operational_status": status or "Update Pending", "delay_minutes": "", "lanes_open": ""}
    stamp = at_local.strftime("At %-I:%M %p ").replace("AM", "am").replace("PM", "pm") + tz
    return {"update_time": stamp, "operational_status": "delay" if minutes else "no delay",
            "delay_minutes": str(minutes), "lanes_open": str(random.randint(1, 4))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    if urlparse(database_url()).hostname not in ("localhost", "127.0.0.1"):
        raise SystemExit("Refusing: demo data may only be written to a localhost database.")

    random.seed(42)
    base = json.loads(FIXTURE.read_text())
    commercial = [r for r in base if r["commercial_vehicle_lanes"].get("maximum_lanes", "N/A").isdigit()]
    busyness = {r["port_number"]: random.uniform(0.3, 2.0) for r in commercial}
    now = datetime.now(timezone.utc).replace(minute=7, second=0, microsecond=0)

    with connect() as conn:
        ensure_schema(conn)
        for h in range(args.days * 24, 0, -1):
            captured = now - timedelta(hours=h)
            payload = copy.deepcopy(base)
            for r in payload:
                if r not in commercial and r["port_number"] not in busyness:
                    continue
                tz = zone_for(r)
                local = (captured + timedelta(hours=OFFSETS.get(tz, -5))).replace(minute=0, tzinfo=None)
                open_hours = 6 <= local.hour <= 22 or r["border"] == "Canadian Border"
                peak = 1.0 + 1.5 * max(0.0, 1 - abs(local.hour - 13) / 5)
                cv = r["commercial_vehicle_lanes"]
                if not open_hours:
                    cv["standard_lanes"] = lane(None, local, tz, "Lanes Closed")
                elif random.random() < 0.12:
                    cv["standard_lanes"] = lane(None, local, tz)
                else:
                    std = max(0, int(random.gauss(20 * busyness[r["port_number"]] * peak, 8)))
                    cv["standard_lanes"] = lane(5 * round(std / 5), local, tz)
                if "FAST_lanes" in cv and cv["FAST_lanes"]["operational_status"] != "N/A":
                    if open_hours and cv["standard_lanes"]["delay_minutes"]:
                        fast = int(int(cv["standard_lanes"]["delay_minutes"]) * random.uniform(0.3, 0.7))
                        cv["FAST_lanes"] = lane(5 * round(fast / 5), local, tz)
                    else:
                        cv["FAST_lanes"] = lane(None, local, tz, "Lanes Closed")
            digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
            with conn.transaction():
                conn.execute(
                    "INSERT INTO raw.cbp_snapshot (captured_at, payload_sha256, record_count, payload) "
                    "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    (captured, digest, len(payload), Jsonb(payload)),
                )
                if random.random() > 0.03:  # a few missed runs, so the health view has gaps
                    conn.execute(
                        "INSERT INTO raw.pipeline_run (job, started_at, finished_at, status, rows_loaded, detail) "
                        "VALUES ('ingest_cbp', %s, %s, 'success', 1, 'DEMO DATA')",
                        (captured, captured + timedelta(seconds=4)),
                    )
    print(f"wrote {args.days * 24} DEMO snapshots")


if __name__ == "__main__":
    main()
