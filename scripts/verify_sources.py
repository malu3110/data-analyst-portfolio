"""Check that the project's public data sources are live and print their shape.

Runs on GitHub Actions (see .github/workflows/verify-sources.yml) so the check
happens from the same network the scheduled pipeline uses.
"""
import json
import sys
from collections import Counter

import requests

CBP_URL = "https://bwt.cbp.gov/api/bwtnew"
BTS_URL = "https://data.bts.gov/resource/keg4-3bc2.json"
HEADERS = {"User-Agent": "cross-border-wait-monitor (portfolio project)"}


def check_cbp() -> bool:
    print(f"== CBP {CBP_URL}")
    r = requests.get(CBP_URL, headers=HEADERS, timeout=60)
    print("HTTP", r.status_code, "|", r.headers.get("content-type"), "|", len(r.content), "bytes")
    if r.status_code != 200:
        return False
    data = r.json()
    print("records:", len(data))
    print("top-level keys:", sorted(data[0].keys()))
    print("borders:", Counter(d.get("border") for d in data))
    commercial = [d for d in data if (d.get("commercial_vehicle_lanes") or {}).get("maximum_lanes") not in (None, "", "N/A")]
    print("crossings with commercial lanes:", len(commercial))
    statuses = Counter()
    for d in commercial:
        for lane in ("standard_lanes", "FAST_lanes"):
            statuses[(lane, d["commercial_vehicle_lanes"].get(lane, {}).get("operational_status"))] += 1
    print("commercial lane statuses:", statuses.most_common(12))
    print("date/time samples:", sorted({(d.get("date"), d.get("time")) for d in data})[:5])
    for d in commercial[:3]:
        print(json.dumps(d, indent=1))
    return True


def check_bts() -> bool:
    print(f"\n== BTS {BTS_URL}")
    params = {"$limit": 3, "$order": "date DESC", "$where": "measure='Trucks'"}
    r = requests.get(BTS_URL, params=params, headers=HEADERS, timeout=60)
    print("HTTP", r.status_code)
    if r.status_code != 200:
        print(r.text[:500])
        return False
    print(json.dumps(r.json(), indent=1))
    r2 = requests.get(BTS_URL, params={"$select": "measure, count(*)", "$group": "measure"}, headers=HEADERS, timeout=60)
    print("measures:", r2.json())
    return True


if __name__ == "__main__":
    ok = check_cbp()
    ok = check_bts() and ok
    sys.exit(0 if ok else 1)
