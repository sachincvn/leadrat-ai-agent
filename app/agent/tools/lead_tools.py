"""Lead tools exposed to the LLM.

Each tool is a thin wrapper over the CRM client — no business logic here.
Docstrings matter: the model reads them to decide which tool to call.
"""

import json

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client
from app.schemas.lead import LeadFilters


@tool
def get_lead(lead_id: str) -> str:
    """Get the details of one lead by its id, for example L001."""
    return get_crm_client().get_lead(lead_id).model_dump_json()


@tool
def search_leads(source: str = "", location: str = "", status: str = "") -> str:
    """Search leads by source (Facebook, Google, Referral), city and/or status.

    Pass only the values the user actually stated. Leave the rest empty.
    """
    filters = LeadFilters(
        source=source or None, location=location or None, status=status or None
    )
    leads = get_crm_client().search_leads(filters)
    return json.dumps([lead.model_dump() for lead in leads], default=str)
