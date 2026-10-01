import os
from pathlib import Path

import psycopg

SCHEMA_SQL = Path(__file__).parent / "sql" / "schema.sql"


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url


def connect(url: str | None = None) -> psycopg.Connection:
    return psycopg.connect(url or database_url())


def ensure_schema(conn: psycopg.Connection) -> None:
    """Create raw tables if missing. Safe to run on every job."""
    with conn.transaction():
        conn.execute(SCHEMA_SQL.read_text())
