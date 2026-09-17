"""Thin HTTP client for the MUSO backend. The UI never calls the agent directly."""

import requests

from ui.config import BASE, REQUEST_TIMEOUT


def _headers(jwt: str | None) -> dict:
    return {"Authorization": f"Bearer {jwt}"} if jwt else {}


def health() -> dict:
    resp = requests.get(f"{BASE}/health", timeout=10)
    resp.raise_for_status()
    return resp.json()


def chat(message: str, lead_id: str | None = None, jwt: str | None = None) -> dict:
    resp = requests.post(
        f"{BASE}/chat",
        json={"message": message, "lead_id": lead_id or None},
        headers=_headers(jwt),
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def get_lead(lead_id: str, jwt: str | None = None) -> dict:
    resp = requests.get(f"{BASE}/leads/{lead_id}", headers=_headers(jwt), timeout=30)
    resp.raise_for_status()
    return resp.json()
