"""POST /listingsite/listing/top-count - listing counts by status.

Confirmed against the live Swagger spec (operation MCP_CountAsyncv1, request
body GetBaseLevelCountForListingManagementRequest -> the same
ListingParameterDto filter shape as listing search, checked 2026-09-17).
"""

from typing import Any

from app.core.logging import get_logger
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.listing import ListingFilters, ListingTopCounts

log = get_logger(__name__)

PATH = "/listingsite/listing/top-count"


def build_body(filters: ListingFilters | None = None) -> dict:
    body: dict[str, Any] = {"pageNumber": 1, "pageSize": 1, "orderBy": []}
    if filters and filters.location:
        body["cities"] = [filters.location]
    return body


def get_listing_top_count(http: LeadratHttp, filters: ListingFilters | None = None) -> ListingTopCounts | None:
    payload = http.post(PATH, build_body(filters))
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return None

    return ListingTopCounts(
        all=data.get("allCount"),
        draft=data.get("draftCount"),
        approved=data.get("approvedCount"),
        refused=data.get("refusedCount"),
        archived=data.get("archivedCount"),
        sold=data.get("soldCount"),
        pending_approval=data.get("pendingApproval"),
        taken_down=data.get("takenDown"),
        expired=data.get("expired"),
        pocket_listing=data.get("pocketListingCount"),
    )
