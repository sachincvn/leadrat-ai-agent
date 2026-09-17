"""Tool: list or search leads via the custom-filters endpoint.

Backed by POST /lead/custom-filters - the lead-search endpoint for tenants
with custom lead statuses. Same filters and response shape as search_leads;
only the underlying Leadrat endpoint differs.
"""

import json

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client
from app.schemas.lead import Lead, LeadFilters

MAX_LEADS = 15
SAMPLE_FIELDS = ("id", "name", "phone", "source", "status", "location", "project", "assigned_to")


def _compact(lead: Lead) -> dict:
    data = lead.model_dump()
    return {key: data[key] for key in SAMPLE_FIELDS if data.get(key)}


@tool
def search_leads_custom_filters(
    keyword: str = "",
    location: str = "",
    source: str = "",
    status: str = "",
    limit: int = 10,
) -> str:
    """List or search the user's leads via the CRM's custom-filters endpoint.

    Use this instead of search_leads only when told to use the custom-filters
    API specifically. The result reports the total number of matching leads
    and a sample of them.

    keyword  - a name or phone number to search for
    location - city
    source   - Facebook, Google Ads, Referral, Walk In, ...
    status   - New, Interested, Qualified, ...
    limit    - how many leads to sample, 1 to 15

    Pass only values the user actually stated. Leave the rest empty.
    """
    filters = LeadFilters(
        keyword=keyword or None,
        location=location or None,
        source=source or None,
        status=status or None,
        limit=max(1, min(limit, MAX_LEADS)),
    )
    page = get_crm_client().search_leads_custom_filters(filters)

    return json.dumps(
        {
            "total_matching_leads": page.total,
            "showing": len(page.leads),
            "leads": [_compact(lead) for lead in page.leads],
        },
        default=str,
    )
