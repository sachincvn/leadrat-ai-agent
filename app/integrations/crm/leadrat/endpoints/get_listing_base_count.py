"""POST /listingsite/listing/base-count - listing counts by category.

Confirmed against the live Swagger spec (operation MCP_CountAsyncv12, request
body GetSecondLevelCountForListingRequest -> the same ListingParameterDto
filter shape as listing search, checked 2026-09-17).
"""

from typing import Any

from app.core.logging import get_logger
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.listing import ListingBaseCounts, ListingFilters

log = get_logger(__name__)

PATH = "/listingsite/listing/base-count"


def build_body(filters: ListingFilters | None = None) -> dict:
    body: dict[str, Any] = {"pageNumber": 1, "pageSize": 1, "orderBy": []}
    if filters and filters.location:
        body["cities"] = [filters.location]
    return body


def get_listing_base_count(http: LeadratHttp, filters: ListingFilters | None = None) -> ListingBaseCounts | None:
    payload = http.post(PATH, build_body(filters))
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return None

    return ListingBaseCounts(
        all=data.get("allCount"),
        residential=data.get("residentialCount"),
        commercial=data.get("commercialCount"),
    )
