"""Read claims out of a Leadrat JWT.

The payload is decoded, never verified — Leadrat verifies the signature itself.
We only need `custom:tenant_id` so the `tenant` header can be filled in
automatically from the caller's own token.
"""

import base64
import json

from app.core.logging import get_logger

log = get_logger(__name__)


def decode_claims(token: str) -> dict:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:  # noqa: BLE001 - a malformed token is not fatal here
        log.warning("Could not decode JWT payload")
        return {}


def tenant_id(token: str) -> str | None:
    return decode_claims(token).get("custom:tenant_id")


def user_id(token: str) -> str | None:
    return decode_claims(token).get("custom:user_id")
