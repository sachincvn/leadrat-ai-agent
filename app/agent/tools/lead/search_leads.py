"""Tool: search leads.

Backed by POST /api/v1/mcp/lead/new/all on the live CRM, or the mock file
in development.
"""

import json

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client
from app.schemas.lead import LeadFilters


@tool
def search_leads(
    keyword: str = "",
    location: str = "",
    source: str = "",
    status: str = "",
    limit: int = 20,
) -> str:
    """Search leads in the CRM.

    keyword  — a name or phone number to search for
    location — city or locality
    source   — Facebook, Google, Referral, ...
    status   — New, Interested, Qualified, ...

    Pass only the values the user actually stated. Leave the rest empty.
    """
    filters = LeadFilters(
        keyword=keyword or None,
        location=location or None,
        source=source or None,
        status=status or None,
        limit=limit,
    )
    leads = get_crm_client().search_leads(filters)
    return json.dumps([lead.model_dump() for lead in leads], default=str)
