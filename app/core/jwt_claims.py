"""Read claims out of a Leadrat JWT.

The payload is decoded, never verified — Leadrat verifies the signature itself.
We only need `custom:tenant_id` so the `tenant` header can be filled in
automatically from the caller's own token.
"""

import base64
import json
from datetime import datetime, timezone
from uuid import UUID

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


# Where the caller's own identity may be hiding, most specific first. Leadrat's
# own MCP server reads "custom:user_id" in its tools and the "sub" subject in
# its profile service, and both go through UUID.fromString - so a claim that is
# not a GUID is not an id at all, whichever one carries it.
_USER_ID_CLAIMS = ("custom:user_id", "user_id", "sub", "uid")

# The same token often carries a login name instead of (or beside) the GUID.
_USER_NAME_CLAIMS = (
    "custom:user_name", "preferred_username", "cognito:username",
    "username", "unique_name", "email", "custom:user_id", "sub",
)


def _is_guid(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        UUID(value)
    except ValueError:
        return False
    return True


def user_id(token: str) -> str | None:
    """The caller's user GUID, or None when the token carries no GUID at all.

    Returning None rather than a non-GUID is the whole point: Leadrat's
    assignTo is typed System.Guid, and sending "surya_sachin" there fails the
    whole request with a 400 instead of just that filter.
    """
    claims = decode_claims(token)
    for claim in _USER_ID_CLAIMS:
        value = claims.get(claim)
        if _is_guid(value):
            return value
    return None


def user_name(token: str) -> str | None:
    """The caller's login name, for tenants whose token carries no user GUID."""
    claims = decode_claims(token)
    for claim in _USER_NAME_CLAIMS:
        value = claims.get(claim)
        if isinstance(value, str) and value.strip() and not _is_guid(value):
            return value.strip()
    return None


def expires_at(token: str) -> datetime | None:
    """When the token stops being valid, from its `exp` claim."""
    exp = decode_claims(token).get("exp")
    if not isinstance(exp, (int, float)):
        return None
    try:
        return datetime.fromtimestamp(exp, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def describe_expiry(token: str) -> str:
    """A short, log-safe account of the token's lifetime.

    Worth its own line whenever the CRM rejects a call: "expired 4 minutes ago"
    and "valid for another 20 minutes" point at completely different problems,
    and guessing between them has already cost an afternoon.
    """
    expiry = expires_at(token)
    if expiry is None:
        return "no exp claim"

    seconds = (expiry - datetime.now(timezone.utc)).total_seconds()
    minutes = abs(seconds) / 60
    if seconds < 0:
        return f"expired {minutes:.0f} min ago (exp {expiry:%Y-%m-%d %H:%M:%S} UTC)"
    return f"valid for another {minutes:.0f} min (exp {expiry:%Y-%m-%d %H:%M:%S} UTC)"
