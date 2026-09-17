"""Tool: the tenant's project-type hierarchy.

Backed by GET /masterdata/masterprojecttypes.
"""

import json

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client


@tool
def list_project_types() -> str:
    """List the valid project types configured for this tenant, including
    their sub-types.

    Use this before filtering by project type, to see the real valid values
    instead of guessing one.
    """
    types = get_crm_client().list_project_types()
    return json.dumps([t.model_dump(exclude_none=True) for t in types], default=str)
