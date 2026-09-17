"""Builds the CRM client for the current request.

The client carries the caller's JWT, so it is built per request rather than
cached — the token differs for every user.
"""

from app.core.context import get_jwt
from app.integrations.crm.leadrat import LeadratClient


def get_crm_client() -> LeadratClient:
    return LeadratClient(jwt=get_jwt() or "")
