import requests

from pipeline import http


class FakeResp:
    def __init__(self, status, body=None):
        self.status_code = status
        self._body = body

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


def test_retries_server_errors_then_succeeds(monkeypatch):
    responses = iter([FakeResp(503), requests.ConnectionError("reset"), FakeResp(200, [1])])

    def fake_get(*args, **kwargs):
        r = next(responses)
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(http.requests, "get", fake_get)
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    assert http.get_json("https://example.test") == [1]


def test_client_error_is_not_retried(monkeypatch):
    calls = []

    def fake_get(*args, **kwargs):
        calls.append(1)
        return FakeResp(404)

    monkeypatch.setattr(http.requests, "get", fake_get)
    try:
        http.get_json("https://example.test")
    except requests.HTTPError:
        pass
    assert len(calls) == 1
