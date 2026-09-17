"""Leadrat CRM client — every method maps to one endpoint module."""

from app.core.exceptions import LeadNotFoundError
from app.integrations.crm.leadrat.endpoints import get_all_leads
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.lead import Lead, LeadFilters


class LeadratClient:
    def __init__(self, jwt: str):
        self._http = LeadratHttp(jwt)

    def get_lead(self, lead_id: str) -> Lead:
        # Leadrat has no single-lead MCP endpoint yet, so fetch by id filter.
        leads = get_all_leads(self._http, LeadFilters(lead_ids=[lead_id]), page_size=1)
        if not leads:
            raise LeadNotFoundError(f"Lead '{lead_id}' not found")
        return leads[0]

    def search_leads(self, filters: LeadFilters) -> list[Lead]:
        return get_all_leads(self._http, filters, page_size=filters.limit)
