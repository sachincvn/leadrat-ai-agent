"""Thin HTTP client for the MUSO backend. The UI never calls the agent directly."""

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
