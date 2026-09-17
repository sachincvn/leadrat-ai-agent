"""POST /property/new/all - search properties with available filters.

Confirmed against the live Swagger spec (operation MCP_Search3, request body
V2GetAllPropertyRequest -> GetAllPropertyParameters, checked 2026-09-17).

pageNumber, pageSize and orderBy are required by the schema (not nullable).
Everything else is optional and omitted entirely when unset.
"""

from typing import Any

from app.core.logging import get_logger
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.property import Property, PropertyFilters, PropertyPage

log = get_logger(__name__)

PATH = "/property/new/all"

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 200


def build_body(filters: PropertyFilters, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE) -> dict:
    body: dict[str, Any] = {
        "pageNumber": max(page, 1),
        "pageSize": min(page_size if page_size > 0 else DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE),
        "orderBy": [],
    }

    if filters.keyword:
        body["keyword"] = filters.keyword
    if filters.location:
        body["cities"] = [filters.location]
    if filters.property_type:
        body["propertyTypes"] = [filters.property_type]
    if filters.min_price is not None:
        body["minPrice"] = filters.min_price
    if filters.max_price is not None:
        body["maxPrice"] = filters.max_price

    return body


def extract_rows(payload: Any) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("items"), list):
        return payload["items"]
    log.warning("Unrecognised property response envelope. Top-level keys: %s", list(payload))
    return []


def total_count(payload: Any) -> int | None:
    if isinstance(payload, dict):
        count = payload.get("totalCount")
        if isinstance(count, int):
            return count
    return None


def _named(value: Any) -> str | None:
    if isinstance(value, dict):
        return value.get("displayName") or value.get("name")
    return value


def to_property(row: dict) -> Property:
    projects = row.get("projects") or []
    return Property(
        id=str(row.get("id") or ""),
        title=row.get("title") or "Unknown",
        status=_named(row.get("status")),
        sale_type=_named(row.get("saleType")),
        furnish_status=_named(row.get("furnishStatus")),
        no_of_bhk=row.get("noOfBHK"),
        project=(projects[0] if projects else row.get("project")),
        unit_no=row.get("unitNo"),
        created_at=row.get("createdOn"),
    )


def get_properties(
    http: LeadratHttp,
    filters: PropertyFilters,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> PropertyPage:
    payload = http.post(PATH, build_body(filters, page, page_size))
    rows = extract_rows(payload)
    total = total_count(payload)
    log.info("get_properties -> %d rows (total %s)", len(rows), total)
    return PropertyPage(total=total, properties=[to_property(row) for row in rows])
