"""GET /lead/histories/{id} - a lead's field-change audit trail.

Confirmed against the live Swagger spec at
https://connect.leadrat.info/swagger/v1/swagger.json (operation under
`/api/v1/mcp/lead/histories/{id}`, GET, checked 2026-09-17). This replaces
the earlier unverified `POST /lead/history` guess, which was 404ing.

Key differences from the old guess:
  - GET, not POST. `id` is a path segment, not a body field.
  - No request body at all - no baseUTcOffset/timeZoneId/pageNumber/pageSize.
    Leadrat returns the lead's *entire* history in one call; there is no
    server-side paging on this endpoint, so `page`/`page_size` are applied
    client-side below.
  - Response envelope is {"succeeded", "message", "errors", "data": [...],
    "actionCode", "isClockInMandatory"} - the rows are under "data", not
    "items".
  - Each row is a field-change audit entry (LeadHistoryDto), not a generic
    activity/timeline item:
        fieldName       - which field changed (e.g. "Status")
        filterKey       - enum: 0=None, 1=Assignment, 2=Notes, 3=Status
        oldValue        - previous value
        newValue        - new value
        updatedBy       - who made the change
        updatedOn       - when (date-time)
        auditActionType - e.g. Create / Update
"""

from typing import Any

from app.core.logging import get_logger
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.lead import LeadHistoryEntry, LeadHistoryPage

log = get_logger(__name__)

PATH = "/lead/histories/{id}"

DEFAULT_PAGE_SIZE = 20

_FILTER_KEY_NAMES = {0: "None", 1: "Assignment", 2: "Notes", 3: "Status"}


def extract_rows(payload: Any) -> list[dict]:
    """Leadrat wraps the list in {"data": [...], "succeeded": true, ...}."""
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    if isinstance(payload, list):
        return payload

    log.warning(
        "Unrecognised lead-history response envelope. Top-level keys: %s",
        list(payload) if isinstance(payload, dict) else type(payload).__name__,
    )
    return []


def _filter_key_name(value: Any) -> str | None:
    """filterKey may come back as the int enum value or (if Leadrat's JSON
    config uses a string-enum converter) as its name directly."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return _FILTER_KEY_NAMES.get(value, str(value))
    if isinstance(value, str) and value:
        return value
    return None


def to_entry(row: dict) -> LeadHistoryEntry:
    return LeadHistoryEntry(
        field_name=row.get("fieldName"),
        category=_filter_key_name(row.get("filterKey")),
        old_value=row.get("oldValue"),
        new_value=row.get("newValue"),
        updated_by=row.get("updatedBy"),
        updated_at=row.get("updatedOn"),
        action_type=row.get("auditActionType"),
    )


def get_lead_history(
    http: LeadratHttp,
    lead_id: str,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> LeadHistoryPage:
    payload = http.get(PATH.format(id=lead_id))
    rows = extract_rows(payload)

    # Client-side paging - Leadrat doesn't page this endpoint.
    page = max(page, 1)
    size = page_size if page_size > 0 else DEFAULT_PAGE_SIZE
    start = (page - 1) * size
    page_rows = rows[start : start + size]

    log.info(
        "get_lead_history(%s) -> %d/%d rows (page %d)",
        lead_id, len(page_rows), len(rows), page,
    )
    return LeadHistoryPage(total=len(rows), entries=[to_entry(row) for row in page_rows])
