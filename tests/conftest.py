import json
import os
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def cbp_payload():
    """A real CBP response captured by .github/workflows/capture-fixtures.yml."""
    return json.loads((FIXTURES / "cbp_snapshot.json").read_text())


@pytest.fixture
def bts_rows():
    return json.loads((FIXTURES / "bts_trucks.json").read_text())


@pytest.fixture
def conn():
    """Connection to a disposable test database (TEST_DATABASE_URL). Raw tables are reset."""
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set")
    from pipeline.db import connect, ensure_schema

    with connect(url) as c:
        c.execute("DROP SCHEMA IF EXISTS raw CASCADE")
        c.commit()
        ensure_schema(c)
        yield c
