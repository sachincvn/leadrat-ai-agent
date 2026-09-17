"""Tool: active-pipeline lead counts, without fetching lead records.

Backed by POST /lead/counts/active - regular (non custom-status) tenants only.
"""

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client
from app.schemas.lead import LeadFilters


@tool
def get_lead_active_counts(
    keyword: str = "",
    location: str = "",
    source: str = "",
    status: str = "",
) -> str:
    """Get active-pipeline lead counts, without fetching the lead records.

    Use this for questions like "how many active leads", "how many overdue
    leads", "how many meetings/site visits scheduled today", "how many
    bookings" - active-pipeline buckets rather than a per-status breakdown.

    keyword  - a name or phone number to search for
    location - city
    source   - Facebook, Google Ads, Referral, Walk In, ...
    status   - New, Interested, Qualified, ...

    Pass only values the user actually stated. Leave the rest empty.
    Returns whichever of active/new/pending/scheduled/overdue/booked/
    site-visit/meeting/callback/invoiced/pool counts the tenant computes -
    fields the backend did not compute come back empty and can be ignored.
    """
    filters = LeadFilters(
        keyword=keyword or None,
        location=location or None,
        source=source or None,
        status=status or None,
    )
    counts = get_crm_client().get_lead_active_counts(filters)
    if counts is None:
        return "{}"
    return counts.model_dump_json(exclude_none=True)
