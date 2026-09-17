"""Thin HTTP client for the MUSO backend. The UI never calls the agent directly."""

import json
from collections.abc import Iterator

import requests

from ui.config import BASE, REQUEST_TIMEOUT


class ApiError(Exception):
    """Carries the backend's own error message, not just the status code."""


def _check(resp: requests.Response) -> dict | list:
    if resp.status_code >= 400:
        try:
            detail = resp.json()["error"]["message"]
        except Exception:
            detail = resp.text[:300]
        raise ApiError(f"{resp.status_code}: {detail}")
    return resp.json()


def _headers(jwt: str | None, tenant: str | None = None) -> dict:
    headers = {}
    if jwt:
        headers["Authorization"] = f"Bearer {jwt}"
    if tenant:
        headers["tenant"] = tenant
    return headers


def health() -> dict:
    return _check(requests.get(f"{BASE}/health", timeout=10))


def chat(message: str, jwt: str | None = None, tenant: str | None = None) -> dict:
    resp = requests.post(
        f"{BASE}/chat",
        json={"message": message},
        headers=_headers(jwt, tenant),
        timeout=REQUEST_TIMEOUT,
    )
    return _check(resp)


def chat_stream(message: str, jwt: str, tenant: str | None = None) -> Iterator[dict]:
    """The chat answer as a stream of events: status, text, done, error.

    Server-sent events, so each event arrives as one `data: {...}` line. The
    connection stays open for the whole turn - `stream=True` matters, without
    it requests would buffer the lot and the streaming would be for nothing.
    """
    with requests.post(
        f"{BASE}/chat/stream",
        json={"message": message},
        headers={**_headers(jwt, tenant), "Accept": "text/event-stream"},
        timeout=REQUEST_TIMEOUT,
        stream=True,
    ) as resp:
        if resp.status_code >= 400:
            _check(resp)  # raises ApiError carrying the backend's message
        for line in resp.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                yield json.loads(line[6:])


def clear_chat_history(jwt: str, tenant: str) -> dict:
    """Forget the caller's server-side conversation memory."""
    resp = requests.delete(
        f"{BASE}/chat/history",
        headers=_headers(jwt, tenant),
        timeout=REQUEST_TIMEOUT,
    )
    return _check(resp)


def search_leads(jwt: str, tenant: str, limit: int = 5) -> dict:
    resp = requests.get(
        f"{BASE}/leads/search",
        params={"limit": limit},
        headers=_headers(jwt, tenant),
        timeout=REQUEST_TIMEOUT,
    )
    return _check(resp)
