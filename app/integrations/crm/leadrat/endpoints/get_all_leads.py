"""POST /api/v1/mcp/lead/new/all — the Leadrat "get all leads" search.

The real request body has ~200 optional fields. We send only what the user
actually asked for; everything omitted keeps Leadrat's own default.

Filters that take enum ids (source, budget, bhkTypes, ...) are not wired yet —
they need the id lookup endpoints. Text and paging filters work today.
"""

from typing import Any

from app.core.logging import get_logger
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.lead import Lead, LeadFilters

log = get_logger(__name__)

PATH = "/api/v1/mcp/lead/new/all"

DEFAULT_PAGE_SIZE = 20

# Response wrappers seen from Leadrat endpoints, in the order we try them.
_LIST_KEYS = ("data", "items", "leads", "result", "results", "records")


def build_body(filters: LeadFilters, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE) -> dict:
    """Translate our small filter model into the Leadrat request body."""
    body: dict[str, Any] = {"pageNumber": page, "pageSize": page_size}

    if filters.keyword:
        body["keyword"] = filters.keyword
        body["searchByNameOrNumber"] = filters.keyword
    if filters.location:
        body["locations"] = [filters.location]
    if filters.lead_ids:
        body["leadIds"] = filters.lead_ids
    if filters.status_ids:
        body["statusIds"] = filters.status_ids
    if filters.assigned_to_ids:
        body["assignTo"] = filters.assigned_to_ids

    # TODO: source / budget / bhkTypes are enum ids in Leadrat — map them once
    #       the lookup endpoints are wired.
    return body


def extract_rows(payload: Any) -> list[dict]:
    """Pull the lead rows out of whatever envelope the API returned."""
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []

    for key in _LIST_KEYS:
        value = payload.get(key)
        if isinstance(value, list):
            return value
        # one level of nesting, e.g. {"data": {"items": [...]}}
        if isinstance(value, dict):
            for inner in _LIST_KEYS:
                if isinstance(value.get(inner), list):
                    return value[inner]

    log.warning("Unrecognised lead response envelope. Top-level keys: %s", list(payload))
    return []


def _first(row: dict, *names: str) -> Any:
    for name in names:
        if row.get(name) not in (None, ""):
            return row[name]
    return None


def to_lead(row: dict) -> Lead:
    """Map one Leadrat row onto our Lead model.

    Field names are best-effort: run scripts/probe_leadrat.py against a real
    tenant, then tighten these to the actual response.
    """
    name = _first(row, "name", "fullName", "customerName", "leadName")
    if not name:
        first = _first(row, "firstName") or ""
        last = _first(row, "lastName") or ""
        name = f"{first} {last}".strip() or "Unknown"

    return Lead(
        id=str(_first(row, "id", "leadId", "serialNumber") or ""),
        name=name,
        phone=_first(row, "phoneNumber", "mobile", "contactNo", "phone"),
        email=_first(row, "email", "emailId"),
        source=_first(row, "sourceName", "source"),
        status=_first(row, "statusName", "status"),
        sub_status=_first(row, "subStatusName", "subStatus"),
        location=_first(row, "location", "city", "locality"),
        project=_first(row, "projectName", "project"),
        budget=_first(row, "budget", "maxBudget", "minBudget"),
        requirement=_first(row, "requirement", "enquiredFor", "propertyType"),
        assigned_to=_first(row, "assignedToName", "assignTo", "assignedTo", "owner"),
        last_contacted_at=str(
            _first(row, "lastContactedOn", "lastModifiedOn", "updatedOn") or ""
        )
        or None,
    )


def get_all_leads(
    http: LeadratHttp,
    filters: LeadFilters,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> list[Lead]:
    payload = http.post(PATH, build_body(filters, page, page_size))
    rows = extract_rows(payload)
    log.info("get_all_leads -> %d rows", len(rows))
    return [to_lead(row) for row in rows]
