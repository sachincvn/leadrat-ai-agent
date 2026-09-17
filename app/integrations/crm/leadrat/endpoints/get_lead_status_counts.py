"""POST /lead/counts/statuses - lead COUNTS per status (regular tenants).

Same filtered request body as get_all_leads. Response envelope:
{"succeeded": true, "data": {"items": [{"statusCount": {"statusId", "count"},
"subStatusCount": [{"statusId", "count"}, ...]}, ...]}}. Ids are resolved to
display names against the master status tree (see get_lead_statuses).
"""

from app.core.logging import get_logger
from app.integrations.crm.leadrat.endpoints.get_all_leads import build_body
from app.integrations.crm.leadrat.endpoints.get_lead_statuses import status_name_map
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.lead import LeadFilters, LeadStatusCount

log = get_logger(__name__)

PATH = "/lead/counts/statuses"


def get_lead_status_counts(http: LeadratHttp, filters: LeadFilters) -> list[LeadStatusCount]:
    body = build_body(filters)
    body["path"] = PATH.lstrip("/")
    payload = http.post(PATH, body)

    data = payload.get("data") if isinstance(payload, dict) else None
    items = data.get("items") if isinstance(data, dict) else None
    items = items if isinstance(items, list) else []
    if not items:
        log.warning("get_lead_status_counts: empty response")
        return []

    name_by_id = status_name_map(http)
    result = []
    for aggregate in items:
        if not isinstance(aggregate, dict):
            continue
        status_count = aggregate.get("statusCount")
        if not isinstance(status_count, dict):
            continue
        sub_counts = [
            LeadStatusCount(name=name_by_id.get(str(s.get("statusId"))), count=s.get("count") or 0)
            for s in (aggregate.get("subStatusCount") or [])
            if isinstance(s, dict)
        ]
        result.append(
            LeadStatusCount(
                name=name_by_id.get(str(status_count.get("statusId"))),
                count=status_count.get("count") or 0,
                sub_status_counts=sub_counts or None,
            )
        )
    return result
