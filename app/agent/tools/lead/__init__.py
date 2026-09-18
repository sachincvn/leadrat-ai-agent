"""Lead tools — one file per CRM API.

search_leads and get_lead_counts each transparently handle both the
"new/all" and "custom-filters" tenant variants (see LeadratClient), so the
model only ever sees one search tool and one counts tool - matching old
mcp's design, where that per-tenant endpoint choice is hidden in the
service layer rather than exposed as extra tools to choose between.

NOTE: get_lead_active_counts.py, get_lead_base_filter_counts.py,
get_lead_counts_custom_filters.py, get_lead_status_counts.py and
search_leads_custom_filters.py in this folder are superseded by
get_lead_counts.py / search_leads.py above and are no longer imported here.
They're harmless (dead code, not registered as tools) but can be deleted.

Adding a tool:
    1. new file in this folder, named after the tool, holding one @tool function
    2. import it below and append it to LEAD_TOOLS
"""

from langchain_core.tools import BaseTool

from app.agent.tools.lead.get_lead import get_lead
from app.agent.tools.lead.get_lead_counts import get_lead_counts
from app.agent.tools.lead.get_lead_history import get_lead_history
from app.agent.tools.lead.search_leads import search_leads
from app.agent.tools.lead.summarize_lead import summarize_lead

LEAD_TOOLS: list[BaseTool] = [
    get_lead,
    search_leads,
    get_lead_counts,
    get_lead_history,
    summarize_lead,
]
