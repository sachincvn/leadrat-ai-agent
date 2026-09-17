"""Master-data tools - one file per CRM API.

Adding a tool:
    1. new file in this folder, named after the tool, holding one @tool function
    2. import it below and append it to MASTERDATA_TOOLS

Only the two lines below are shared, so parallel work rarely conflicts.
"""

from langchain_core.tools import BaseTool

from app.agent.tools.masterdata.list_amenity_categories import list_amenity_categories
from app.agent.tools.masterdata.list_area_units import list_area_units
from app.agent.tools.masterdata.list_project_types import list_project_types
from app.agent.tools.masterdata.list_property_types import list_property_types
from app.agent.tools.masterdata.list_statuses import list_statuses

MASTERDATA_TOOLS: list[BaseTool] = [
    list_property_types,
    list_project_types,
    list_area_units,
    list_statuses,
    list_amenity_categories,
]
