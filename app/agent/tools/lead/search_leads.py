"""Tool: list or search leads.

Backed by POST /lead/new/all.

The tenant can hold six figures of leads, so the tool never hands the model a
large page: it returns the total match count plus a small sample with only the
fields worth reasoning about. A bigger page would blow the model's context and
the inference API would reject the request outright.
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
def search_leads(
    keyword: str = "",
    location: str = "",
    source: str = "",
    status: str = "",
    limit: int = 10,
) -> str:
    """List or search the user's leads in the CRM.

    Call with no arguments for an overview of the user's leads - that is the
    right call for "show my leads", "get all leads" or "how many leads do I have".
    The result reports the total number of matching leads and a sample of them.

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
    page = get_crm_client().search_leads(filters)

    return json.dumps(
        {
            "total_matching_leads": page.total,
            "showing": len(page.leads),
            "leads": [_compact(lead) for lead in page.leads],
        },
        default=str,
    )
