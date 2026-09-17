"""Leadrat CRM client - every method maps to one endpoint module."""

from app.core.exceptions import LeadNotFoundError
from app.integrations.crm.leadrat.endpoints import get_all_leads
from app.integrations.crm.leadrat.endpoints.get_leads_custom_filters import get_leads_custom_filters
from app.integrations.crm.leadrat.endpoints.get_leads_custom_filters_count import get_leads_custom_filters_count
from app.integrations.crm.leadrat.endpoints.get_lead_active_counts import get_lead_active_counts
from app.integrations.crm.leadrat.endpoints.get_lead_base_filter_counts import get_lead_base_filter_counts
from app.integrations.crm.leadrat.endpoints.get_lead_status_counts import get_lead_status_counts
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.lead import Lead, LeadActiveCounts, LeadBaseFilterCounts, LeadFilters, LeadPage, LeadStatusCount


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

    def search_leads_custom_filters(self, filters: LeadFilters) -> LeadPage:
        return get_leads_custom_filters(self._http, filters, page_size=filters.limit)

    def get_leads_custom_filters_count(self, filters: LeadFilters) -> list[LeadStatusCount]:
        return get_leads_custom_filters_count(self._http, filters)

    def get_lead_status_counts(self, filters: LeadFilters) -> list[LeadStatusCount]:
        return get_lead_status_counts(self._http, filters)

    def get_lead_base_filter_counts(self, filters: LeadFilters) -> LeadBaseFilterCounts | None:
        return get_lead_base_filter_counts(self._http, filters)

    def get_lead_active_counts(self, filters: LeadFilters) -> LeadActiveCounts | None:
        return get_lead_active_counts(self._http, filters)
