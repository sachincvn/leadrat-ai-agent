"""Lead tools — one file per CRM API.

Adding a tool:
    1. new file in this folder, named after the tool, holding one @tool function
    2. import it below and append it to LEAD_TOOLS

Only the two lines below are shared, so parallel work rarely conflicts.

Planned (see product.md section 7):
    get_lead_history.py  get_lead_calls.py  get_lead_tasks.py  apply_lead_filter.py
"""

from langchain_core.tools import BaseTool

from app.agent.tools.lead.get_lead import get_lead
from app.agent.tools.lead.get_lead_base_filter_counts import get_lead_base_filter_counts
from app.agent.tools.lead.get_lead_counts_custom_filters import get_lead_counts_custom_filters
from app.agent.tools.lead.get_lead_status_counts import get_lead_status_counts
from app.agent.tools.lead.search_leads import search_leads
from app.agent.tools.lead.search_leads_custom_filters import search_leads_custom_filters

LEAD_TOOLS: list[BaseTool] = [
    get_lead,
    search_leads,
    search_leads_custom_filters,
    get_lead_counts_custom_filters,
    get_lead_status_counts,
    get_lead_base_filter_counts,
]
