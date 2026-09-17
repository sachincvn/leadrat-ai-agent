"""Tool: list every user in the tenant, with their roles.

Backed by GET /user/getalluserswithroles.
"""

import json

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client


@tool
def list_users() -> str:
    """List every user (teammate) in the tenant with their id, name, and roles.

    Use this to resolve a name to a user id before calling get_user_profile -
    e.g. "who is Priya", "who manages the sales team". Also answers "who's
    on my team" / "list all users" directly.
    """
    users = get_crm_client().list_users()
    return json.dumps([u.model_dump(exclude_none=True) for u in users], default=str)
