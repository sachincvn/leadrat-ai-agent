"""Leadrat CRM client - every method maps to one endpoint module."""

from app.core.exceptions import LeadNotFoundError, UserNotFoundError
from app.core.jwt_claims import user_id as jwt_user_id
from app.integrations.crm.leadrat.endpoints import (
    get_all_leads,
    get_all_users,
    get_lead_history,
    get_user_profile,
)
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.lead import Lead, LeadFilters, LeadHistoryPage, LeadPage
from app.schemas.user import UserProfile, UserSummary


class LeadratClient:
    def __init__(self, jwt: str, tenant: str):
        self._jwt = jwt
        self._http = LeadratHttp(jwt, tenant)

    def get_lead(self, lead_id: str) -> Lead:
        # Leadrat has no single-lead MCP endpoint yet, so fetch by id filter.
        page = get_all_leads(self._http, LeadFilters(lead_ids=[lead_id]), page_size=1)
        if not page.leads:
            raise LeadNotFoundError(f"Lead '{lead_id}' not found")
        return page.leads[0]

    def search_leads(self, filters: LeadFilters) -> LeadPage:
        return get_all_leads(self._http, filters, page_size=filters.limit)

    def get_lead_history(self, lead_id: str, limit: int = 20) -> LeadHistoryPage:
        return get_lead_history(self._http, lead_id, page_size=limit)

    def get_user_profile(self, user_id: str) -> UserProfile:
        profile = get_user_profile(self._http, user_id)
        if not profile.user_id:
            raise UserNotFoundError(f"User '{user_id}' not found")
        return profile

    def get_my_profile(self) -> UserProfile:
        # The caller's own id is embedded in their JWT - no lookup needed.
        my_id = jwt_user_id(self._jwt) if self._jwt else None
        if not my_id:
            raise UserNotFoundError("Could not determine the caller's user id from their JWT")
        return self.get_user_profile(my_id)

    def list_users(self) -> list[UserSummary]:
        return get_all_users(self._http)
