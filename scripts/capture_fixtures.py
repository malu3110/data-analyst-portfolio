"""Save a real CBP snapshot and recent BTS truck rows to tests/fixtures/.

Run by .github/workflows/capture-fixtures.yml, which commits the files, so tests
run against real source data rather than hand-made mocks.
"""
import json
from pathlib import Path

import requests

HEADERS = {"User-Agent": "cross-border-wait-monitor (portfolio project)"}


FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def emit(name: str, obj) -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    (FIXTURES / name).write_text(json.dumps(obj, indent=1) + "\n")
    print(f"wrote {name}: {len(obj)} records")


cbp = requests.get("https://bwt.cbp.gov/api/bwtnew", headers=HEADERS, timeout=60).json()
emit("cbp_snapshot.json", cbp)

bts = requests.get(
    "https://data.bts.gov/resource/keg4-3bc2.json",
    params={"$where": "measure='Trucks' AND date >= '2024-09-01'", "$limit": 50000,
            "$select": "port_name,state,port_code,border,date,measure,value"},
    headers=HEADERS, timeout=120,
).json()
emit("bts_trucks.json", bts)
