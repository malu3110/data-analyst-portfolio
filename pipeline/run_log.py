from contextlib import contextmanager

import psycopg


class Run:
    def __init__(self) -> None:
        self.rows_loaded = 0
        self.detail: str | None = None


@contextmanager
def logged_run(conn: psycopg.Connection, job: str):
    """Record start/finish of a job in raw.pipeline_run.

    The data load runs in its own transaction, so a failure never leaves a
    partial load; the failure itself is still recorded here, then re-raised so
    the scheduler marks the run as failed.
    """
    with conn.transaction():
        run_id = conn.execute(
            "INSERT INTO raw.pipeline_run (job) VALUES (%s) RETURNING run_id", (job,)
        ).fetchone()[0]
    run = Run()
    try:
        yield run
    except Exception as exc:
        with conn.transaction():
            conn.execute(
                "UPDATE raw.pipeline_run SET finished_at = now(), status = 'failed', detail = %s "
                "WHERE run_id = %s",
                (f"{type(exc).__name__}: {exc}"[:2000], run_id),
            )
        raise
    with conn.transaction():
        conn.execute(
            "UPDATE raw.pipeline_run SET finished_at = now(), status = 'success', "
            "rows_loaded = %s, detail = %s WHERE run_id = %s",
            (run.rows_loaded, run.detail, run_id),
        )
