"""The tool set the agent is allowed to use.

Tools are grouped by CRM module, one package per module, one file per API.
Register a new module by importing its list and adding it here.
"""

from langchain_core.tools import BaseTool

from app.agent.tools.lead import LEAD_TOOLS
from app.agent.tools.user import USER_TOOLS

TOOLS: list[BaseTool] = [
    *LEAD_TOOLS,
    *USER_TOOLS,
    # *TASK_TOOLS,
    # *MEETING_TOOLS,
]

TOOLS_BY_NAME: dict[str, BaseTool] = {t.name: t for t in TOOLS}
