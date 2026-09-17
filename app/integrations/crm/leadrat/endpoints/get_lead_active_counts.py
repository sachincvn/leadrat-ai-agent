"""POST /lead/counts/active - active-pipeline lead counts (regular tenants only).

Same filtered request body as get_all_leads. Response envelope:
{"succeeded": true, "data": {...counts...}}.
"""

from app.core.logging import get_logger
from app.integrations.crm.leadrat.endpoints.get_all_leads import build_body
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.lead import LeadActiveCounts, LeadFilters

log = get_logger(__name__)

PATH = "/lead/counts/active"


def get_lead_active_counts(http: LeadratHttp, filters: LeadFilters) -> LeadActiveCounts | None:
    body = build_body(filters)
    body["path"] = PATH.lstrip("/")
    payload = http.post(PATH, body)

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        log.warning("get_lead_active_counts: empty response")
        return None

    return LeadActiveCounts(
        active_leads_count=data.get("activeLeadsCount"),
        new_leads_count=data.get("newLeadsCount"),
        pending_leads_count=data.get("pendingLeadsCount"),
        scheduled_leads_count=data.get("scheduledLeadsCount"),
        overdue_leads_count=data.get("overdueLeadsCount"),
        booked_leads_count=data.get("bookedLeadsCount"),
        scheduled_today_leads_count=data.get("scheduledTodayLeadsCount"),
        scheduled_tomorrow_leads_count=data.get("scheduledTomorrowLeadsCount"),
        scheduled_next_two_days_leads_count=data.get("scheduledNextTwoDaysLeadsCount"),
        upcoming_scheduled_leads_count=data.get("upcomingScheduledLeadsCount"),
        site_visits_count=data.get("siteVisitsCount"),
        meetings_count=data.get("meetingsCount"),
        callback_count=data.get("callbackCount"),
        all_leads_count=data.get("allLeadsCount"),
        overdue_meeting_count=data.get("overdueMeetingCount"),
        overdue_site_visit_count=data.get("overdueSiteVisitCount"),
        overdue_callback_count=data.get("overdueCallbackCount"),
        booking_cancel_lead_count=data.get("bookingCancelLeadCount"),
        expression_of_interest_lead_count=data.get("expressionOfInterestLeadCount"),
        invoiced_leads_count=data.get("invoicedLeadsCount"),
        pool_leads_count=data.get("poolLeadsCount"),
    )
