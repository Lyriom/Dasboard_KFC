from __future__ import annotations

import pytest
import httpx

from app.windsor import WindsorClient, WindsorError


class FakeSettings:
    windsor_api_key = "super-secret-key"
    windsor_base_url = "https://connectors.windsor.ai"
    http_timeout_seconds = 60
    http_retries = 1


def test_windsor_error_includes_http_status_body_and_redacts_secret(monkeypatch) -> None:
    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url, params):
            request = httpx.Request("GET", url, params=params)
            return httpx.Response(
                400,
                request=request,
                json={"error": f"bad key {params['api_key']}"},
            )

    monkeypatch.setattr("app.windsor.httpx.Client", FakeClient)

    client = WindsorClient(FakeSettings())
    with pytest.raises(WindsorError) as exc:
        client._get_rows("/facebook", {"api_key": "super-secret-key", "fields": "date"})

    message = str(exc.value)
    assert "HTTP 400" in message
    assert "body=" in message
    assert "bad key ***REDACTED***" in message
    assert "super-secret-key" not in message
