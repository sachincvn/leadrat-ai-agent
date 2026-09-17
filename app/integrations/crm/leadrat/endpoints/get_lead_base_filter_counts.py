"""POST /lead/new/counts/basefilter - generic base-filter lead counts.

Same filtered request body as get_all_leads. Independent of tenant type
(custom-status or regular) - always available alongside the per-status
breakdown. Response envelope: {"succeeded": true, "data": {...counts...}}.
"""

from app.core.logging import get_logger
from app.integrations.crm.leadrat.endpoints.get_all_leads import build_body
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.lead import LeadBaseFilterCounts, LeadFilters

log = get_logger(__name__)

PATH = "/lead/new/counts/basefilter"


def get_lead_base_filter_counts(http: LeadratHttp, filters: LeadFilters) -> LeadBaseFilterCounts | None:
    body = build_body(filters)
    body["path"] = PATH.lstrip("/")
    payload = http.post(PATH, body)

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        log.warning("get_lead_base_filter_counts: empty response")
        return None

    return LeadBaseFilterCounts(
        all_leads_count=data.get("allLeadsCount") or 0,
        my_leads_count=data.get("myLeadsCount") or 0,
        team_leads_count=data.get("teamLeadsCount") or 0,
        unassign_leads_count=data.get("unassignLeadsCount"),
        deleted_leads_count=data.get("deletedLeadsCount") or 0,
        duplicate_leads_count=data.get("duplicateLeadsCount") or 0,
        re_enquired_leads_count=data.get("reEnquiredLeadsCount") or 0,
        pending_assignment_leads_count=data.get("pendingAssignmentLeadsCount") or 0,
    )
