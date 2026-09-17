"""Tool: lead COUNTS by custom filters, without fetching lead records.

Backed by POST /lead/custom-filters-count-level1 - the lead-count endpoint for
tenants with custom lead statuses. Same filters as search_leads_custom_filters,
but returns per-status (and nested per-sub-status) counts instead of leads.
"""

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client
from app.schemas.lead import LeadFilters


@tool
def get_lead_counts_custom_filters(
    keyword: str = "",
    location: str = "",
    source: str = "",
    status: str = "",
) -> str:
    """Get lead COUNTS by status (and nested sub-status) via the CRM's
    custom-filters-count endpoint, without fetching the lead records.

    Use this instead of search_leads_custom_filters whenever the user only
    wants a count / "how many" for a custom-status tenant - e.g. "how many
    leads in each status", "count of New leads" - not the lead details.

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
    counts = get_crm_client().get_leads_custom_filters_count(filters)
    return "[" + ",".join(c.model_dump_json(exclude_none=True) for c in counts) + "]"
