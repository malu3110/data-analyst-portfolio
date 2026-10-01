import pytest

from pipeline.run_log import logged_run


def test_success_is_recorded(conn):
    with logged_run(conn, "job_a") as run:
        run.rows_loaded = 7
    status, rows = conn.execute("select status, rows_loaded from raw.pipeline_run").fetchone()
    assert (status, rows) == ("success", 7)


def test_failure_is_recorded_and_reraised(conn):
    with pytest.raises(RuntimeError):
        with logged_run(conn, "job_b"):
            raise RuntimeError("source down")
    status, detail, finished = conn.execute(
        "select status, detail, finished_at from raw.pipeline_run"
    ).fetchone()
    assert status == "failed"
    assert "source down" in detail
    assert finished is not None
