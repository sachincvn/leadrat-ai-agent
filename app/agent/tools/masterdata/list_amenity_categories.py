"""Tool: amenity categories and their amenities.

Backed by GET /customamenityandattribute/get/all/categories/with/amenities.
"""

import json

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client


@tool
def list_amenity_categories() -> str:
    """List the amenity categories (e.g. "Safety", "Recreation") and the
    amenities in each, configured for this tenant.

    Use this before filtering properties/projects by amenity, to see the
    real valid values instead of guessing one.
    """
    categories = get_crm_client().list_amenity_categories()
    return json.dumps([c.model_dump(exclude_none=True) for c in categories], default=str)
