from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any, Optional

import httpx

from app.config import Settings


class WindsorError(RuntimeError):
    pass


logging.getLogger("httpx").setLevel(logging.WARNING)


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
        last_message: Optional[str] = None
        retries = max(1, self.settings.http_retries)
        for attempt in range(retries):
            response: Optional[httpx.Response] = None
            try:
                with httpx.Client(timeout=self.settings.http_timeout_seconds) as client:
                    response = client.get(url, params=params)
                    response.raise_for_status()
                    return _extract_rows(response.json())
            except httpx.HTTPStatusError as exc:
                last_error = exc
                last_message = _http_error_message(path, exc.response, params)
            except httpx.HTTPError as exc:
                last_error = exc
                last_message = (
                    f"Windsor request failed for {path}: {exc.__class__.__name__}; "
                    f"url={_safe_request_url(url, params)}"
                )
            except ValueError as exc:
                last_error = exc
                last_message = (
                    f"Windsor request failed for {path}: invalid JSON response; "
                    f"url={_safe_request_url(url, params)}; "
                    f"body={_response_body(response, params)}"
                )
            except WindsorError as exc:
                last_error = exc
                last_message = (
                    f"Windsor request failed for {path}: {exc}; "
                    f"url={_safe_request_url(url, params)}; "
                    f"body={_response_body(response, params)}"
                )
            if last_error:
                if attempt + 1 >= retries:
                    break
                time.sleep(0.5 * (2**attempt))
        raise WindsorError(last_message or f"Windsor request failed for {path}") from last_error


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


def _http_error_message(
    path: str,
    response: httpx.Response,
    params: dict[str, Any],
) -> str:
    return (
        f"Windsor request failed for {path}: HTTP {response.status_code}; "
        f"url={_safe_request_url(str(response.request.url).split('?')[0], params)}; "
        f"body={_response_body(response, params)}"
    )


def _safe_request_url(url: str, params: dict[str, Any]) -> str:
    request = httpx.Request("GET", url, params=_redacted_params(params))
    return str(request.url)


def _redacted_params(params: dict[str, Any]) -> dict[str, Any]:
    return {
        key: "***REDACTED***" if key in {"api_key", "access_token"} else value
        for key, value in params.items()
    }


def _response_body(
    response: Optional[httpx.Response],
    params: dict[str, Any],
    *,
    limit: int = 2000,
) -> str:
    if response is None:
        return ""
    body = response.text[:limit]
    return _redact_text(body, params)


def _redact_text(text: str, params: dict[str, Any]) -> str:
    redacted = text
    for key in ("api_key", "access_token"):
        secret = params.get(key)
        if secret:
            redacted = redacted.replace(str(secret), "***REDACTED***")
    return redacted
