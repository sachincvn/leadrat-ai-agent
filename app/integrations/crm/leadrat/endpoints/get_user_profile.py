"""GET /userprofile/{id} - one user's profile.

Confirmed against the live Swagger spec at
https://connect.leadrat.info/swagger/v1/swagger.json (operation under
`/api/v1/mcp/userprofile/{id}`, GET, checked 2026-09-17).

No request body - id is a path segment. Response is wrapped the same way as
lead history: {"succeeded", "message", "errors", "data": {...}, ...}. The raw
`data` object carries ~50 fields (documents, role permissions, general
settings, time zone, mcpConnect flags, ...) - `to_profile()` below keeps only
what's useful for the agent; everything else is dropped on the floor.

designation / department / reportsTo come back as nested objects
({"id", "name"} / {"id", "name", "contactNo"}) - `_name()` pulls out the
display name.
"""

from typing import Any

from app.core.logging import get_logger
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.user import UserProfile

log = get_logger(__name__)

PATH = "/userprofile/{id}"


def extract_data(payload: Any) -> dict:
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return payload["data"]

    log.warning(
        "Unrecognised user-profile response envelope. Top-level keys: %s",
        list(payload) if isinstance(payload, dict) else type(payload).__name__,
    )
    return {}


def _name(obj: Any) -> str | None:
    return obj.get("name") if isinstance(obj, dict) else None


def to_profile(row: dict) -> UserProfile:
    roles = row.get("userRoles") or []
    return UserProfile(
        user_id=str(row.get("userId") or ""),
        user_name=row.get("userName"),
        first_name=row.get("firstName"),
        last_name=row.get("lastName"),
        email=row.get("email"),
        phone_number=row.get("phoneNumber"),
        is_active=row.get("isActive"),
        designation=_name(row.get("designation")),
        department=_name(row.get("department")),
        reports_to=_name(row.get("reportsTo")),
        office_name=row.get("officeName"),
        lead_count=row.get("leadCount"),
        roles=[r.get("name") for r in roles if isinstance(r, dict) and r.get("name")],
    )


def get_user_profile(http: LeadratHttp, user_id: str) -> UserProfile:
    payload = http.get(PATH.format(id=user_id))
    row = extract_data(payload)
    log.info("get_user_profile(%s) -> %s", user_id, "found" if row else "empty")
    return to_profile(row)


def extract_permissions(row: dict) -> set[str]:
    """The flat permission set behind a profile's roles.

    Shaped like rolePermission[].permissions[] - the same place Leadrat's MCP
    server reads, so "Permissions.Leads.ViewAllLeads" and friends mean exactly
    what they mean there.
    """
    permissions: set[str] = set()
    for role in row.get("rolePermission") or []:
        if not isinstance(role, dict):
            continue
        for permission in role.get("permissions") or []:
            if isinstance(permission, str):
                permissions.add(permission)
    return permissions


def get_user_permissions(http: LeadratHttp, user_id: str) -> set[str]:
    """Just the caller's permissions, for the checks that gate a lead request."""
    row = extract_data(http.get(PATH.format(id=user_id)))
    permissions = extract_permissions(row)
    log.info("get_user_permissions(%s) -> %d permission(s)", user_id, len(permissions))
    return permissions
