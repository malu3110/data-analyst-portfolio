import time

import requests

HEADERS = {"User-Agent": "cross-border-wait-monitor (github.com/malu3110/data-analyst-portfolio)"}


def get_json(url: str, params: dict | None = None, attempts: int = 4, timeout: int = 60):
    """GET with exponential backoff on network errors and 5xx responses."""
    for attempt in range(1, attempts + 1):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
            if resp.status_code < 500:
                resp.raise_for_status()
                return resp.json()
            error: Exception = requests.HTTPError(f"HTTP {resp.status_code}")
        except (requests.ConnectionError, requests.Timeout) as exc:
            error = exc
        if attempt == attempts:
            raise error
        time.sleep(2**attempt)
