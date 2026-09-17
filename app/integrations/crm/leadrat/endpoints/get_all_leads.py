"""POST /lead/new/all - the Leadrat lead search.

The request body has ~200 optional fields, but a few are compulsory on every
call and Leadrat answers 500 without them:

    baseUTcOffset, timeZoneId, path, pageNumber, pageSize

Empty strings are rejected for typed fields, so a filter the user did not give
is omitted rather than sent as "".
"""

from typing import Any

from app.core.logging import get_logger
from app.integrations.crm.leadrat.http import LeadratHttp
from app.integrations.crm.leadrat.lead_sources import code_for, display_name
from app.schemas.lead import Lead, LeadFilters, LeadPage

log = get_logger(__name__)

PATH = "/lead/new/all"

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 500

BASE_UTC_OFFSET = "05:30:00"
TIME_ZONE_ID = "Asia/Calcutta"


def build_body(filters: LeadFilters, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE) -> dict:
    """Translate our filter model into the Leadrat request body."""
    body: dict[str, Any] = {
        # compulsory on every request
        "baseUTcOffset": BASE_UTC_OFFSET,
        "timeZoneId": TIME_ZONE_ID,
        "path": PATH.lstrip("/"),
        "pageNumber": max(page, 1),
        "pageSize": min(page_size if page_size > 0 else DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE),
        "CanAccessAllLeads": True,
    }

    # Optional filters. Omitted entirely when unset - never sent as "" or null.
    if filters.keyword:
        body["SearchByNameOrNumber"] = filters.keyword
    if filters.location:
        body["cities"] = [filters.location]
    if filters.lead_ids:
        body["leadIds"] = filters.lead_ids
    if filters.status_ids:
        body["statusIds"] = filters.status_ids
    if filters.assigned_to_ids:
        body["assignTo"] = filters.assigned_to_ids
    if filters.source:
        code = code_for(filters.source)
        if code is not None:
            body["source"] = [code]
        else:
            log.warning("Unknown lead source '%s' - filter ignored", filters.source)

    return body


def extract_rows(payload: Any) -> list[dict]:
    """This endpoint returns {"items": [...], "totalCount": n, "succeeded": true}."""
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []

    if isinstance(payload.get("items"), list):
        return payload["items"]

    # count endpoints wrap the same shape one level deeper
    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return data["items"]

    log.warning("Unrecognised lead response envelope. Top-level keys: %s", list(payload))
    return []


def total_count(payload: Any) -> int | None:
    if isinstance(payload, dict):
        count = payload.get("totalCount")
        if isinstance(count, int):
            return count
    return None


def to_lead(row: dict) -> Lead:
    """Map one Leadrat row onto our Lead model."""
    status = row.get("status") or {}
    enquiry = row.get("enquiry") or {}
    address = row.get("address") or {}
    projects = row.get("projects") or []

    location = (
        address.get("city")
        or address.get("locality")
        or address.get("subLocality")
        or address.get("state")
    )

    return Lead(
        id=str(row.get("id") or ""),
        name=row.get("name") or "Unknown",
        phone=row.get("contactNo"),
        email=row.get("email"),
        source=display_name(enquiry.get("leadSource")),
        sub_source=enquiry.get("subSource"),
        status=status.get("displayName") or status.get("status"),
        location=location,
        project=projects[0].get("name") if projects else None,
        requirement=row.get("notes"),
        assigned_to=row.get("assignTo"),
        scheduled_at=row.get("scheduledDate"),
        created_at=row.get("createdOn"),
        last_modified_at=row.get("lastModifiedOn"),
        lead_number=row.get("leadNumber") or row.get("serialNumber"),
    )


def get_all_leads(
    http: LeadratHttp,
    filters: LeadFilters,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> LeadPage:
    payload = http.post(PATH, build_body(filters, page, page_size))
    rows = extract_rows(payload)
    total = total_count(payload)
    log.info("get_all_leads -> %d rows (total %s)", len(rows), total)
    return LeadPage(total=total, leads=[to_lead(row) for row in rows])
