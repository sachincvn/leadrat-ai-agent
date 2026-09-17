"""GET /status - the tenant's configured lead-status tree.

Confirmed against the live Swagger spec (operation under `/api/v1/mcp/status`,
"Get all status.", GET, checked 2026-09-17). Requires the tenant header like
most endpoints (unlike the masterdata/* trio, which don't).

Unlike propertytypes/masterprojecttypes/masterareaunits, this one *does*
accept query params - PageNumber/PageSize/OrderBy/Keyword/AdvancedFilter.* -
all optional, no default documented in the spec. To avoid silently getting
back a truncated first page, PageSize is passed explicitly high; tighten
DEFAULT_PAGE_SIZE if a live call shows the tenant has more statuses than that.

Same {"items": [...], "itemsCount", "totalCount"} envelope as the masterdata
endpoints. Rows can nest via `childTypes` (sub-statuses), mapped recursively.
"""

from typing import Any

from app.core.logging import get_logger
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.masterdata import LeadStatus

log = get_logger(__name__)

PATH = "/status"

DEFAULT_PAGE_SIZE = 200


def build_query(page_size: int = DEFAULT_PAGE_SIZE) -> dict:
    return {"PageNumber": 1, "PageSize": page_size}


def extract_items(payload: Any) -> list[dict]:
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload["items"]

    log.warning(
        "Unrecognised status-list response envelope. Top-level keys: %s",
        list(payload) if isinstance(payload, dict) else type(payload).__name__,
    )
    return []


def to_status(row: dict) -> LeadStatus:
    children = row.get("childTypes") or []
    return LeadStatus(
        id=str(row.get("id") or ""),
        status=row.get("status"),
        display_name=row.get("displayName"),
        order_rank=row.get("orderRank"),
        is_active=row.get("isActive"),
        is_default=row.get("isDefault"),
        color=row.get("color"),
        children=[to_status(c) for c in children if isinstance(c, dict)],
    )


def get_statuses(http: LeadratHttp) -> list[LeadStatus]:
    payload = http.get(PATH, params=build_query())
    rows = extract_items(payload)
    log.info("get_statuses -> %d top-level rows", len(rows))
    return [to_status(row) for row in rows]
