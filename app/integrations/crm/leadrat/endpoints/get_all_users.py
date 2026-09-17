"""GET /user/getalluserswithroles - every user in the tenant, with roles.

Confirmed against the live Swagger spec at
https://connect.leadrat.info/swagger/v1/swagger.json (operation under
`/api/v1/mcp/user/getalluserswithroles`, GET, checked 2026-09-17).

No request body, no query params beyond the standard tenant header, and no
pagination - Leadrat returns every user in one call. Response:
{"succeeded", "message", "errors", "data": [{"id", "userName", "firstName",
"lastName", "isActive", "userRoles": [{"roleId", "name"}]}], ...}.

Used to resolve a name to a user id before calling get_user_profile -
the same two-step shape as search_leads -> get_lead.
"""

from typing import Any

from app.core.logging import get_logger
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.user import UserSummary

log = get_logger(__name__)

PATH = "/user/getalluserswithroles"


def extract_rows(payload: Any) -> list[dict]:
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    if isinstance(payload, list):
        return payload

    log.warning(
        "Unrecognised user-list response envelope. Top-level keys: %s",
        list(payload) if isinstance(payload, dict) else type(payload).__name__,
    )
    return []


def to_summary(row: dict) -> UserSummary:
    roles = row.get("userRoles") or []
    return UserSummary(
        id=str(row.get("id") or ""),
        user_name=row.get("userName"),
        first_name=row.get("firstName"),
        last_name=row.get("lastName"),
        is_active=row.get("isActive"),
        roles=[r.get("name") for r in roles if isinstance(r, dict) and r.get("name")],
    )


def get_all_users(http: LeadratHttp) -> list[UserSummary]:
    payload = http.get(PATH)
    rows = extract_rows(payload)
    log.info("get_all_users -> %d rows", len(rows))
    return [to_summary(row) for row in rows]
