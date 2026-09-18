"""The tool set the agent is allowed to use.

Tools are grouped by CRM module, one package per module, one file per API.
Register a new module by importing its list and adding it here.
"""

from langchain_core.tools import BaseTool

from app.agent.tools.lead import LEAD_TOOLS
from app.agent.tools.listing import LISTING_TOOLS
from app.agent.tools.masterdata import MASTERDATA_TOOLS
from app.agent.tools.project import PROJECT_TOOLS
from app.agent.tools.report import REPORT_TOOLS
from app.agent.tools.property import PROPERTY_TOOLS
from app.agent.tools.settings import SETTINGS_TOOLS
from app.agent.tools.user import USER_TOOLS

TOOLS: list[BaseTool] = [
    *LEAD_TOOLS,
    *USER_TOOLS,
    *MASTERDATA_TOOLS,
    *PROJECT_TOOLS,
    *PROPERTY_TOOLS,
    *LISTING_TOOLS,
    *SETTINGS_TOOLS,
    *REPORT_TOOLS,
    # *TASK_TOOLS,
    # *MEETING_TOOLS,
]

TOOLS_BY_NAME: dict[str, BaseTool] = {t.name: t for t in TOOLS}
