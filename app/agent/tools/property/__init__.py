"""Property tools, one file per API."""

from app.agent.tools.property.get_property_count import get_property_count
from app.agent.tools.property.list_properties import list_properties

PROPERTY_TOOLS = [list_properties, get_property_count]
