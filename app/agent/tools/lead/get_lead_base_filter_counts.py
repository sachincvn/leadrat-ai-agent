"""Tool: generic base-filter lead counts, without fetching lead records.

Backed by POST /lead/new/counts/basefilter - available for any tenant,
regardless of custom-status setup.
"""

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client
from app.schemas.lead import LeadFilters


@tool
def get_lead_base_filter_counts(
    keyword: str = "",
    location: str = "",
    source: str = "",
    status: str = "",
) -> str:
    """Get generic base-filter lead counts, without fetching the lead records.

    Use this for questions like "how many leads do I have in total", "how
    many unassigned leads", "how many duplicate leads", "how many leads
    pending assignment" - counts that aren't broken down by status.

    keyword  - a name or phone number to search for
    location - city
    source   - Facebook, Google Ads, Referral, Walk In, ...
    status   - New, Interested, Qualified, ...

    Pass only values the user actually stated. Leave the rest empty.
    Returns all_leads_count, my_leads_count, team_leads_count,
    unassign_leads_count, deleted_leads_count, duplicate_leads_count,
    re_enquired_leads_count, pending_assignment_leads_count.
    """
    filters = LeadFilters(
        keyword=keyword or None,
        location=location or None,
        source=source or None,
        status=status or None,
    )
    counts = get_crm_client().get_lead_base_filter_counts(filters)
    if counts is None:
        return "{}"
    return counts.model_dump_json(exclude_none=True)
