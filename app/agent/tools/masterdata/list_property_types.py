"""Tool: the tenant's property-type hierarchy.

Backed by GET /masterdata/propertytypes.
"""

import json

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client


@tool
def list_property_types() -> str:
    """List the valid property types (e.g. Residential -> Apartment, Villa)
    configured for this tenant, including their sub-types.

    Use this before filtering leads/properties by property type, to see the
    real valid values instead of guessing one.
    """
    types = get_crm_client().list_property_types()
    return json.dumps([t.model_dump(exclude_none=True) for t in types], default=str)
