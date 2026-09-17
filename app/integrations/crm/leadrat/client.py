"""Leadrat CRM client - every method maps to one endpoint module."""

from app.core.exceptions import LeadNotFoundError
from app.integrations.crm.leadrat.endpoints import get_all_leads
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.lead import Lead, LeadFilters, LeadPage


class LeadratClient:
    def __init__(self, jwt: str, tenant: str):
        self._http = LeadratHttp(jwt, tenant)

    def get_lead(self, lead_id: str) -> Lead:
        # Leadrat has no single-lead MCP endpoint yet, so fetch by id filter.
        page = get_all_leads(self._http, LeadFilters(lead_ids=[lead_id]), page_size=1)
        if not page.leads:
            raise LeadNotFoundError(f"Lead '{lead_id}' not found")
        return page.leads[0]

    def search_leads(self, filters: LeadFilters) -> LeadPage:
        return get_all_leads(self._http, filters, page_size=filters.limit)
