"""Tool: list or search properties.

Backed by POST /property/new/all.
"""

import json

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client
from app.schemas.property import Property, PropertyFilters

MAX_PROPERTIES = 15
SAMPLE_FIELDS = ("id", "title", "status", "sale_type", "furnish_status", "no_of_bhk", "project")


def _compact(prop: Property) -> dict:
    data = prop.model_dump()
    return {key: data[key] for key in SAMPLE_FIELDS if data.get(key) is not None}


@tool
def list_properties(keyword: str = "", location: str = "", property_type: str = "", limit: int = 10) -> str:
    """List or search the tenant's property listings (units for sale/rent).

    Call with no arguments for "show all properties" or "how many properties
    do we have". The result reports the total number of matching properties
    and a sample of them.

    keyword       - a property title to search for
    location      - city
    property_type - check list_property_types first if unsure of valid values

    Pass only values the user actually stated. Leave the rest empty.
    """
    filters = PropertyFilters(
        keyword=keyword or None,
        location=location or None,
        property_type=property_type or None,
        limit=max(1, min(limit, MAX_PROPERTIES)),
    )
    page = get_crm_client().search_properties(filters)

    return json.dumps(
        {
            "total_matching_properties": page.total,
            "showing": len(page.properties),
            "properties": [_compact(p) for p in page.properties],
        },
        default=str,
    )
