"""HTTP session for the Leadrat API.

Every call carries the caller's JWT and tenant, so Leadrat applies that user's
own permissions.
"""

import uuid
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import AuthError, CRMError
from app.core.logging import get_logger

log = get_logger(__name__)

_TOKEN_ERROR_MARKERS = ("CanReadToken", "IDX12", "not well formed", "token is expired")


def _is_token_error(body: str) -> bool:
    return any(marker in body for marker in _TOKEN_ERROR_MARKERS)


def _message(resp: httpx.Response) -> str:
    """Leadrat's own explanation, so a 500 says what it disliked."""
    try:
        body = resp.json()
    except ValueError:
        return resp.text[:300]

    if isinstance(body, dict):
        for key in ("messages", "message", "detail", "title", "error", "exception"):
            value = body.get(key)
            if isinstance(value, list) and value:
                return str(value[0])[:300]
            if isinstance(value, str) and value:
                return value[:300]
    return str(body)[:300]


class LeadratHttp:
    def __init__(self, jwt: str, tenant: str):
        if not jwt:
            raise AuthError("No Leadrat JWT available for this request")
        if not tenant:
            raise AuthError("No Leadrat tenant available for this request")

        self.headers = {
            "Authorization": f"Bearer {jwt}",
            "tenant": tenant,
            "accept": "application/json",
            "Content-Type": "application/json",
        }

    def _request_headers(self) -> dict:
        # Leadrat correlates a call across its services by this id.
        return {**self.headers, "X-Correlation-Id": str(uuid.uuid4())}

    def _handle_response(self, path: str, resp: httpx.Response) -> Any:
        if resp.status_code in (401, 403):
            raise AuthError("Leadrat rejected the JWT (expired or not permitted)")

        # Leadrat answers a malformed or expired token with a 500 whose body
        # names the token problem, so read the body before calling it a server error.
        if resp.status_code >= 400 and _is_token_error(resp.text):
            raise AuthError("Leadrat could not read the JWT - it is malformed or expired")

        if resp.status_code >= 400:
            log.error("Leadrat %s -> %s %s", path, resp.status_code, resp.text[:1000])
            raise CRMError(f"Leadrat returned {resp.status_code}: {_message(resp)}")

        return resp.json()

    def post(self, path: str, body: dict) -> Any:
        url = f"{settings.leadrat_base_url}{path}"
        log.info("POST %s body=%s", path, body)
        try:
            resp = httpx.post(
                url, json=body, headers=self._request_headers(), timeout=settings.leadrat_timeout
            )
        except httpx.HTTPError as exc:
            raise CRMError(f"Leadrat request failed: {exc}") from exc

        return self._handle_response(path, resp)

    def get(self, path: str, params: dict | None = None) -> Any:
        url = f"{settings.leadrat_base_url}{path}"
        log.info("GET %s params=%s", path, params)
        try:
            resp = httpx.get(
                url,
                params=params,
                headers=self._request_headers(),
                timeout=settings.leadrat_timeout,
            )
        except httpx.HTTPError as exc:
            raise CRMError(f"Leadrat request failed: {exc}") from exc

        return self._handle_response(path, resp)
