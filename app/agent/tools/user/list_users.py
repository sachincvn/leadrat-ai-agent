"""Tool: list every user in the tenant, with their roles.

Backed by GET /user/getalluserswithroles.
"""

import json
from collections import Counter

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client


@tool
def list_users() -> str:
    """List every user (teammate) in the tenant with their id, name, and roles.

    Returns pre-computed totals - total_users, active_users, inactive_users,
    counts_by_role - alongside the full user list. Report those totals
    directly; don't recount them yourself from the user list, and don't try
    to enumerate every user of a large tenant in the answer - a couple of
    examples per role is enough.

    Use this to resolve a name to a user id before calling get_user_profile -
    e.g. "who is Priya", "who manages the sales team". Also answers "who's
    on my team" / "list all users" directly.
    """
    users = get_crm_client().list_users()

    role_counts: Counter[str] = Counter()
    for u in users:
        for role in u.roles or []:
            role_counts[role] += 1

    return json.dumps(
        {
            "total_users": len(users),
            "active_users": sum(1 for u in users if u.is_active),
            "inactive_users": sum(1 for u in users if not u.is_active),
            "counts_by_role": dict(role_counts),
            "users": [u.model_dump(exclude_none=True) for u in users],
        },
        default=str,
    )
