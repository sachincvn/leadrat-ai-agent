"""POST /lead/custom-filters-count-level1 - lead COUNTS by custom filters.

Same filtered request body as get_all_leads/get_leads_custom_filters, but
returns per-status (and nested per-sub-status) counts instead of lead records.
Response envelope: {"succeeded": true, "message": ..., "data": [...]}, each
item shaped {"name", "count", "childType": [...]}.
"""

from app.core.logging import get_logger
from app.integrations.crm.leadrat.endpoints.get_all_leads import build_body
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.lead import LeadFilters, LeadStatusCount

log = get_logger(__name__)

PATH = "/lead/custom-filters-count-level1"


def _to_status_count(row: dict) -> LeadStatusCount:
    children = row.get("childType") or []
    return LeadStatusCount(
        name=row.get("name"),
        count=row.get("count") or 0,
        sub_status_counts=[_to_status_count(c) for c in children if isinstance(c, dict)] or None,
    )


def get_leads_custom_filters_count(http: LeadratHttp, filters: LeadFilters) -> list[LeadStatusCount]:
    body = build_body(filters)
    body["path"] = PATH.lstrip("/")
    payload = http.post(PATH, body)
    rows = payload.get("data") if isinstance(payload, dict) else None
    rows = rows if isinstance(rows, list) else []
    log.info("get_leads_custom_filters_count -> %d status rows", len(rows))
    return [_to_status_count(row) for row in rows if isinstance(row, dict)]
