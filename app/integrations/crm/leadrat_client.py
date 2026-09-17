"""Live Leadrat CRM client.

Authenticates with the calling user's JWT, so the CRM enforces that user's own
permissions and tenant. Endpoint paths below are placeholders — swap them for
the real Leadrat routes; the return types must stay the same.
"""

from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import AuthError, CRMError, LeadNotFoundError
from app.integrations.crm.base import CRMClient
from app.schemas.lead import Lead, LeadFilters

TIMEOUT = 30


class LeadratClient(CRMClient):
    def __init__(self, jwt: str | None):
        if not jwt:
            raise AuthError("No Leadrat JWT available for this request")
        self._headers = {
            "Authorization": f"Bearer {jwt}",
            "Accept": "application/json",
        }

    def _get(self, path: str, params: dict | None = None) -> Any:
        try:
            resp = httpx.get(
                f"{settings.leadrat_base_url}{path}",
                params=params,
                headers=self._headers,
                timeout=TIMEOUT,
            )
        except httpx.HTTPError as exc:
            raise CRMError(f"CRM request failed: {exc}") from exc

        if resp.status_code in (401, 403):
            raise AuthError("Leadrat rejected the JWT (expired or not permitted)")
        if resp.status_code == 404:
            raise LeadNotFoundError(f"Not found: {path}")
        if resp.status_code >= 400:
            raise CRMError(f"CRM returned {resp.status_code}")
        return resp.json()

    def get_lead(self, lead_id: str) -> Lead:
        return Lead(**self._get(f"/api/leads/{lead_id}"))

    def search_leads(self, filters: LeadFilters) -> list[Lead]:
        data = self._get("/api/leads/search", params=filters.model_dump(exclude_none=True))
        return [Lead(**row) for row in data.get("items", [])]
