"""Derive the PG* variables dbt needs from DATABASE_URL.

In GitHub Actions: masks the password in logs and appends the variables to
$GITHUB_ENV (written as plain KEY=value lines, so special characters in the
password are never shell-parsed). Locally: prints them.
"""
import os
from urllib.parse import parse_qs, unquote, urlparse

url = urlparse(os.environ["DATABASE_URL"])
password = unquote(url.password or "")
lines = [
    f"PGHOST={url.hostname}",
    f"PGPORT={url.port or 5432}",
    f"PGUSER={unquote(url.username or '')}",
    f"PGPASSWORD={password}",
    f"PGDATABASE={url.path.lstrip('/')}",
    f"PGSSLMODE={parse_qs(url.query).get('sslmode', ['require'])[0]}",
]

github_env = os.environ.get("GITHUB_ENV")
if github_env:
    if password:
        print(f"::add-mask::{password}")
    with open(github_env, "a") as fh:
        fh.write("\n".join(lines) + "\n")
    print("dbt connection settings exported")
else:
    print("\n".join(lines))
