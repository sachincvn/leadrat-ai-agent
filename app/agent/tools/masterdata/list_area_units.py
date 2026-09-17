"""Tool: the tenant's area units (sq.ft, acre, ...).

Backed by GET /masterdata/masterareaunits.
"""

import json

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client


@tool
def list_area_units() -> str:
    """List the area units (e.g. sq.ft, acre) configured for this tenant."""
    units = get_crm_client().list_area_units()
    return json.dumps([u.model_dump(exclude_none=True) for u in units], default=str)
