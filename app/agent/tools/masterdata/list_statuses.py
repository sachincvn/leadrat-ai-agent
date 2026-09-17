"""Tool: the tenant's configured lead-status tree.

Backed by GET /status.
"""

import json

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client


@tool
def list_statuses() -> str:
    """List the valid lead statuses configured for this tenant, including
    any sub-statuses.

    Use this before filtering leads by status, or before saying a status
    change is valid/invalid - never guess a status name.
    """
    statuses = get_crm_client().list_statuses()
    return json.dumps([s.model_dump(exclude_none=True) for s in statuses], default=str)
