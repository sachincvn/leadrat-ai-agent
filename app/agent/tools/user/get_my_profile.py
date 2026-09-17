"""Tool: the caller's own profile.

Backed by GET /userprofile/{id}, using the id embedded in the caller's own
JWT (custom:user_id) - no lookup needed, unlike get_user_profile.
"""

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client


@tool
def get_my_profile() -> str:
    """Get the current user's own profile: contact details, designation,
    department, who they report to, and their lead count.

    Use this for "my profile", "who do I report to", "what's my
    designation" - anything about the caller themself. No arguments needed.
    """
    return get_crm_client().get_my_profile().model_dump_json(exclude_none=True)
