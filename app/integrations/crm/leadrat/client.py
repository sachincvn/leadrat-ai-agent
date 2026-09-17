"""Leadrat CRM client - every method maps to one endpoint module."""

from app.core.exceptions import CRMError, LeadNotFoundError, UserNotFoundError
from app.core.jwt_claims import user_id as jwt_user_id
from app.core.logging import get_logger
from app.integrations.crm.leadrat.endpoints import (
    get_all_leads,
    get_all_users,
    get_amenity_categories,
    get_area_units,
    get_global_settings,
    get_lead_history,
    get_listing_base_count,
    get_listing_top_count,
    get_listings,
    get_project_count,
    get_project_leads_count,
    get_project_types,
    get_projects,
    get_properties,
    get_property_count,
    get_property_types,
    get_statuses,
    get_user_profile,
)
from app.integrations.crm.leadrat.endpoints.get_leads_custom_filters import get_leads_custom_filters
from app.integrations.crm.leadrat.endpoints.get_leads_custom_filters_count import get_leads_custom_filters_count
from app.integrations.crm.leadrat.endpoints.get_lead_active_counts import get_lead_active_counts
from app.integrations.crm.leadrat.endpoints.get_lead_base_filter_counts import get_lead_base_filter_counts
from app.integrations.crm.leadrat.endpoints.get_lead_status_counts import get_lead_status_counts
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.global_settings import GlobalSettings
from app.schemas.lead import (
    Lead,
    LeadCounts,
    LeadFilters,
    LeadHistoryPage,
    LeadPage,
)
from app.schemas.listing import ListingBaseCounts, ListingFilters, ListingPage, ListingTopCounts
from app.schemas.masterdata import AmenityCategory, AreaUnit, LeadStatus, ProjectType, PropertyType
from app.schemas.project import ProjectCounts, ProjectFilters, ProjectLeadCount, ProjectPage
from app.schemas.property import PropertyCounts, PropertyFilters, PropertyPage
from app.schemas.user import UserProfile, UserSummary

log = get_logger(__name__)


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
        # Most tenants search "new/all"; a custom-lead-status tenant's data
        # only shows up through "custom-filters" instead. There's no cheap
        # way to know which a tenant is ahead of time, so try the common
        # path first and fall back once rather than exposing both as
        # separate tools the model would have to choose between (old mcp
        # hides this same choice inside its LeadService).
        try:
            return get_all_leads(self._http, filters, page_size=filters.limit)
        except CRMError as exc:
            log.warning("search_leads: /lead/new/all failed (%s), retrying via custom-filters", exc)
            return get_leads_custom_filters(self._http, filters, page_size=filters.limit)

    def get_lead_counts(self, filters: LeadFilters) -> LeadCounts:
        """Up to three independent count breakdowns for one filter, matching
        old mcp's single get_lead_counts tool: per-status counts, generic
        base-filter totals, and (when the tenant has it) active-pipeline
        totals.
        """
        try:
            status_counts = get_lead_status_counts(self._http, filters)
        except CRMError as exc:
            log.warning("get_lead_counts: /lead/counts/statuses failed (%s), retrying via custom-filters", exc)
            status_counts = get_leads_custom_filters_count(self._http, filters)

        base_filter_counts = get_lead_base_filter_counts(self._http, filters)

        try:
            active_counts = get_lead_active_counts(self._http, filters)
        except CRMError as exc:
            log.info("get_lead_counts: active-pipeline counts unavailable for this tenant (%s)", exc)
            active_counts = None

        return LeadCounts(
            status_counts=status_counts,
            base_filter_counts=base_filter_counts,
            active_counts=active_counts,
        )

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

    def list_property_types(self) -> list[PropertyType]:
        return get_property_types(self._http)

    def list_project_types(self) -> list[ProjectType]:
        return get_project_types(self._http)

    def list_area_units(self) -> list[AreaUnit]:
        return get_area_units(self._http)

    def list_statuses(self) -> list[LeadStatus]:
        return get_statuses(self._http)

    def list_amenity_categories(self) -> list[AmenityCategory]:
        return get_amenity_categories(self._http)

    def search_projects(self, filters: ProjectFilters) -> ProjectPage:
        return get_projects(self._http, filters, page_size=filters.limit)

    def get_project_count(self, filters: ProjectFilters | None = None) -> ProjectCounts | None:
        return get_project_count(self._http, filters)

    def get_project_leads_count(self, project_ids: list[str]) -> list[ProjectLeadCount]:
        return get_project_leads_count(self._http, project_ids)

    def search_properties(self, filters: PropertyFilters) -> PropertyPage:
        return get_properties(self._http, filters, page_size=filters.limit)

    def get_property_count(self, filters: PropertyFilters | None = None) -> PropertyCounts | None:
        return get_property_count(self._http, filters)

    def search_listings(self, filters: ListingFilters) -> ListingPage:
        return get_listings(self._http, filters, page_size=filters.limit)

    def get_listing_top_count(self, filters: ListingFilters | None = None) -> ListingTopCounts | None:
        return get_listing_top_count(self._http, filters)

    def get_listing_base_count(self, filters: ListingFilters | None = None) -> ListingBaseCounts | None:
        return get_listing_base_count(self._http, filters)

    def get_global_settings(self) -> GlobalSettings | None:
        return get_global_settings(self._http)
