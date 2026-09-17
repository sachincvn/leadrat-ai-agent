"""Builds the CRM client for the current request.

The client carries the caller's JWT and tenant, so it is built per request
rather than cached — both differ for every user.
"""

from app.core.context import get_jwt, get_tenant
from app.integrations.crm.leadrat import LeadratClient


def get_crm_client() -> LeadratClient:
    return LeadratClient(jwt=get_jwt() or "", tenant=get_tenant() or "")
