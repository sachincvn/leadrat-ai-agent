"""Tool: one user's profile by id.

Backed by GET /userprofile/{id}.
"""

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client


@tool
def get_user_profile(user_id: str) -> str:
    """Get one user's (teammate's) profile: contact details, designation,
    department, who they report to, and their lead count.

    user_id - the user's id (a guid). Don't have it? Call list_users first
    to find it from a name - never guess an id.
    """
    return get_crm_client().get_user_profile(user_id).model_dump_json(exclude_none=True)
