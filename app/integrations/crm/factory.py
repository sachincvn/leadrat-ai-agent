"""Chooses the CRM implementation. The only place that knows both exist.

The live client is built per request because it carries the caller's JWT.
"""

from app.core.config import settings
from app.core.context import get_jwt
from app.integrations.crm.base import CRMClient
from app.integrations.crm.leadrat import LeadratClient
from app.integrations.crm.mock_client import MockCRMClient

_mock = MockCRMClient()


def get_crm_client() -> CRMClient:
    if settings.use_mock_crm:
        return _mock
    return LeadratClient(jwt=get_jwt() or "")
