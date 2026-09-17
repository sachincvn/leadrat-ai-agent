"""Tool: lead COUNTS by status, without fetching lead records.

Backed by POST /lead/counts/statuses - the lead-count-by-status endpoint for
regular (non custom-status) tenants. Same filters as search_leads, but
returns per-status (and nested per-sub-status) counts instead of leads.
"""

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client
from app.schemas.lead import LeadFilters


@tool
def get_lead_status_counts(
    keyword: str = "",
    location: str = "",
    source: str = "",
    status: str = "",
) -> str:
    """Get lead COUNTS by status (and nested sub-status), without fetching the
    lead records themselves.

    Use this instead of search_leads whenever the user only wants a count /
    "how many" broken down by status - e.g. "how many leads in each status",
    "count of New leads" - not the lead details.

    keyword  - a name or phone number to search for
    location - city
    source   - Facebook, Google Ads, Referral, Walk In, ...
    status   - New, Interested, Qualified, ...

    Pass only values the user actually stated. Leave the rest empty.
    Returns a list of {name, count, sub_status_counts}.
    """
    filters = LeadFilters(
        keyword=keyword or None,
        location=location or None,
        source=source or None,
        status=status or None,
    )
    counts = get_crm_client().get_lead_status_counts(filters)
    return "[" + ",".join(c.model_dump_json(exclude_none=True) for c in counts) + "]"
