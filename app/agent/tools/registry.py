"""The tool set the agent is allowed to use.

To add a capability: write the tool in a *_tools.py module, then register it here.

Planned next (see product.md section 14):
    get_lead_history, get_lead_calls, get_lead_tasks, apply_lead_filter
"""

from langchain_core.tools import BaseTool

from app.agent.tools.lead_tools import get_lead, search_leads

TOOLS: list[BaseTool] = [get_lead, search_leads]
TOOLS_BY_NAME: dict[str, BaseTool] = {t.name: t for t in TOOLS}
