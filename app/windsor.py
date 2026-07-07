from __future__ import annotations

import time
from datetime import date
from typing import Any, Optional

import httpx

from app.config import Settings


class WindsorError(RuntimeError):
    pass


class WindsorClient:
    def __init__(self, settings: Settings):
        if not settings.windsor_api_key:
            raise WindsorError("WINDSOR_API_KEY is not configured")
        self.settings = settings
        self.base_url = settings.windsor_base_url.rstrip("/")

    def fetch_connector(
        self,
        connector: str,
        fields: list[str],
        date_from: date,
        date_to: date,
    ) -> list[dict[str, Any]]:
        params = {
            "api_key": self.settings.windsor_api_key,
            "fields": ",".join(fields),
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "_renderer": "json",
        }
        return self._get_rows(f"/{connector}", params=params)

    def fetch_fields(self, connector: str) -> list[dict[str, Any]]:
        return self._get_rows(
            f"/{connector}/fields",
            params={"api_key": self.settings.windsor_api_key},
        )

    def fetch_options(self, connector: str) -> list[dict[str, Any]]:
        return self._get_rows(
            f"/{connector}/options",
            params={"api_key": self.settings.windsor_api_key},
        )

    def _get_rows(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        url = f"{self.base_url}{path}"
        last_error: Optional[Exception] = None
        retries = max(1, self.settings.http_retries)
        for attempt in range(retries):
            try:
                with httpx.Client(timeout=self.settings.http_timeout_seconds) as client:
                    response = client.get(url, params=params)
                    response.raise_for_status()
                    return _extract_rows(response.json())
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt + 1 >= retries:
                    break
                time.sleep(0.5 * (2**attempt))
        raise WindsorError(f"Windsor request failed for {path}: {last_error}") from last_error


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("data", "rows", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
        if all(not isinstance(value, list) for value in payload.values()):
            return [payload]
    raise WindsorError("Unexpected Windsor response shape")
