"""Tool: top-level property counts by category.

Backed by POST /property/count.
"""

import json

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client


@tool
def get_property_count() -> str:
    """Get the total number of properties, broken down by category
    (residential, commercial, agricultural).

    Use this for "how many properties total", "how many commercial
    properties" - counts only, not the property list itself (use
    list_properties for that).
    """
    counts = get_crm_client().get_property_count()
    if counts is None:
        return json.dumps({"error": "No count data returned"})
    return counts.model_dump_json(exclude_none=True)
