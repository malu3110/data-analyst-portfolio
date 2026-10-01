"""Print a real CBP snapshot and recent BTS truck rows as gzip+base64 blocks.

Used once to create tests/fixtures/ from live data (this dev environment cannot
reach the sources directly; GitHub Actions can). Decode with scripts/decode_fixture.py.
"""
import base64
import gzip
import json

import requests

HEADERS = {"User-Agent": "cross-border-wait-monitor (portfolio project)"}


def emit(name: str, obj) -> None:
    blob = base64.b64encode(gzip.compress(json.dumps(obj).encode())).decode()
    print(f"BEGIN {name}")
    for i in range(0, len(blob), 200):
        print(blob[i : i + 200])
    print(f"END {name}")


cbp = requests.get("https://bwt.cbp.gov/api/bwtnew", headers=HEADERS, timeout=60).json()
emit("cbp_snapshot.json", cbp)

bts = requests.get(
    "https://data.bts.gov/resource/keg4-3bc2.json",
    params={"$where": "measure='Trucks' AND date >= '2024-09-01'", "$limit": 50000,
            "$select": "port_name,state,port_code,border,date,measure,value"},
    headers=HEADERS, timeout=120,
).json()
emit("bts_trucks.json", bts)
