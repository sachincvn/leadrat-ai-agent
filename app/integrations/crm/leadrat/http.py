"""HTTP session for the Leadrat API.

Every call carries the caller's JWT and the tenant it belongs to, so Leadrat
applies that user's own permissions.
"""

from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import AuthError, CRMError
from app.core.jwt_claims import tenant_id
from app.core.logging import get_logger

log = get_logger(__name__)


class LeadratHttp:
    def __init__(self, jwt: str):
        if not jwt:
            raise AuthError("No Leadrat JWT available for this request")

        tenant = settings.leadrat_tenant or tenant_id(jwt)
        if not tenant:
            raise AuthError("Could not determine the tenant for this JWT")

        self.headers = {
            "Authorization": f"Bearer {jwt}",
            "tenant": tenant,
            "accept": "application/json",
            "Content-Type": "application/json",
        }

    def post(self, path: str, body: dict) -> Any:
        url = f"{settings.leadrat_base_url}{path}"
        try:
            resp = httpx.post(
                url, json=body, headers=self.headers, timeout=settings.leadrat_timeout
            )
        except httpx.HTTPError as exc:
            raise CRMError(f"Leadrat request failed: {exc}") from exc

        if resp.status_code in (401, 403):
            raise AuthError("Leadrat rejected the JWT (expired or not permitted)")
        if resp.status_code >= 400:
            log.error("Leadrat %s -> %s %s", path, resp.status_code, resp.text[:300])
            raise CRMError(f"Leadrat returned {resp.status_code}")

        return resp.json()
