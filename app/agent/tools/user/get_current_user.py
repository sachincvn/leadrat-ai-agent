"""Tool: the caller's own identity, read straight from their JWT.

Matches old mcp's get_current_user: no CRM API call at all - the caller's
name, username, email, phone, tenant and internal ids are already sitting in
the validated JWT claims, so this is instant and works even if Leadrat's own
API is slow or down. Distinct from get_my_profile, which calls
GET /userprofile/{id} for CRM-side details (designation, department, who
they report to, lead count) that aren't in the token.
"""

import json

from langchain_core.tools import tool

from app.core.context import get_jwt
from app.core.jwt_claims import decode_claims


@tool
def get_current_user() -> str:
    """Get the currently logged-in user's identity: full name, first/last
    name, username, email, phone, tenant, and internal user/GUID ids.

    Use whenever the user asks about themselves at the identity level - "who
    am I", "what's my name", "which tenant am I in", "what's my email". For
    CRM details like designation, department, who they report to, or their
    lead count, use get_my_profile instead.

    Report name/email/tenant to the person; the internal "sub" GUID is for
    reference only - don't recite it unless explicitly asked. No arguments.
    """
    jwt = get_jwt()
    if not jwt:
        return json.dumps({"success": False, "error": "Not authenticated - no user identity available."})

    claims = decode_claims(jwt)
    given_name = claims.get("given_name") or ""
    family_name = claims.get("family_name") or ""
    full_name = f"{given_name} {family_name}".strip()

    return json.dumps(
        {
            "full_name": full_name or None,
            "given_name": given_name or None,
            "family_name": family_name or None,
            "username": claims.get("cognito:username"),
            "email": claims.get("email"),
            "phone": claims.get("phone_number"),
            "tenant_id": claims.get("custom:tenant_id"),
            "user_id": claims.get("custom:user_id"),
            "sub": claims.get("sub"),
        },
        default=str,
    )
