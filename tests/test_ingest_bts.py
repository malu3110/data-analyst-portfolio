import pytest

from pipeline.ingest_bts import replace_rows


def test_full_refresh_replaces_rows(conn, bts_rows):
    assert replace_rows(conn, bts_rows) == len(bts_rows)
    assert replace_rows(conn, bts_rows[:10]) == 10
    assert conn.execute("select count(*) from raw.bts_truck_crossing").fetchone()[0] == 10


def test_empty_response_keeps_existing_data(conn, bts_rows):
    replace_rows(conn, bts_rows[:5])
    with pytest.raises(ValueError, match="no rows"):
        replace_rows(conn, [])
    assert conn.execute("select count(*) from raw.bts_truck_crossing").fetchone()[0] == 5
