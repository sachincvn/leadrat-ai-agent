"""POST /listingsite/all - search listings with available filters.

Confirmed against the live Swagger spec (operation MCP_GetAllListingAsyncv1,
request body GetAllListingRequest -> ListingParameterDto, checked 2026-09-17).

pageNumber, pageSize and orderBy are required by the schema (not nullable).
Everything else is optional and omitted entirely when unset.
"""

from typing import Any

from app.core.logging import get_logger
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.listing import Listing, ListingFilters, ListingPage

log = get_logger(__name__)

PATH = "/listingsite/all"

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 200


def build_body(filters: ListingFilters, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE) -> dict:
    body: dict[str, Any] = {
        "pageNumber": max(page, 1),
        "pageSize": min(page_size if page_size > 0 else DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE),
        "orderBy": [],
    }

    if filters.keyword:
        body["listingSearch"] = filters.keyword
    if filters.location:
        body["cities"] = [filters.location]
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
    log.warning("Unrecognised listing response envelope. Top-level keys: %s", list(payload))
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


def to_listing(row: dict) -> Listing:
    return Listing(
        id=str(row.get("id") or ""),
        title=row.get("title") or "Unknown",
        status=_named(row.get("listingStatus")),
        project=row.get("project"),
        no_of_bedroom=row.get("noOfBedroom"),
        no_of_bathroom=row.get("noOfBathroom"),
        unit_number=row.get("unitNumber"),
        lead_count=row.get("leadCount"),
        created_at=row.get("createdOn"),
    )


def get_listings(
    http: LeadratHttp,
    filters: ListingFilters,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> ListingPage:
    payload = http.post(PATH, build_body(filters, page, page_size))
    rows = extract_rows(payload)
    total = total_count(payload)
    log.info("get_listings -> %d rows (total %s)", len(rows), total)
    return ListingPage(total=total, listings=[to_listing(row) for row in rows])
