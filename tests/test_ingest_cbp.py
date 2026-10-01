import copy

import pytest

from pipeline.ingest_cbp import SchemaError, payload_hash, store_snapshot, validate


def test_real_payload_passes_validation(cbp_payload):
    validate(cbp_payload)


@pytest.mark.parametrize("bad", [[], {}, None])
def test_rejects_non_array_or_empty(bad):
    with pytest.raises(SchemaError):
        validate(bad)


def test_rejects_missing_field(cbp_payload):
    broken = copy.deepcopy(cbp_payload)
    del broken[0]["commercial_vehicle_lanes"]
    with pytest.raises(SchemaError, match="commercial_vehicle_lanes"):
        validate(broken)


def test_rejects_renamed_lane_field(cbp_payload):
    broken = copy.deepcopy(cbp_payload)
    lane = broken[0]["commercial_vehicle_lanes"]["standard_lanes"]
    lane["delay_mins"] = lane.pop("delay_minutes")
    with pytest.raises(SchemaError, match="delay_minutes"):
        validate(broken)


def test_hash_ignores_key_order(cbp_payload):
    reordered = [dict(reversed(list(r.items()))) for r in cbp_payload]
    assert payload_hash(reordered) == payload_hash(cbp_payload)


def test_identical_snapshot_stored_once(conn, cbp_payload):
    assert store_snapshot(conn, cbp_payload) == 1
    assert store_snapshot(conn, cbp_payload) == 0
    changed = copy.deepcopy(cbp_payload)
    changed[0]["time"] = "23:59:59"
    assert store_snapshot(conn, changed) == 1
    assert conn.execute("select count(*) from raw.cbp_snapshot").fetchone()[0] == 2


def test_invalid_snapshot_not_stored(conn):
    with pytest.raises(SchemaError):
        store_snapshot(conn, [{"port_number": "1"}])
    assert conn.execute("select count(*) from raw.cbp_snapshot").fetchone()[0] == 0
