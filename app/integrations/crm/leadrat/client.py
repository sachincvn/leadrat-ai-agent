"""Leadrat CRM client - every method maps to one endpoint module."""

from app.core.exceptions import CRMError, LeadNotFoundError, UserNotFoundError
from app.core.jwt_claims import user_id as jwt_user_id
from app.core.jwt_claims import user_name as jwt_user_name
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
from app.integrations.crm.leadrat.endpoints.get_user_profile import get_user_permissions
from app.integrations.crm.leadrat.endpoints.run_report import run_report
from app.integrations.crm.leadrat.http import LeadratHttp
from app.integrations.crm.leadrat.tenant_profile import (
    REPORT_ALL_USERS,
    REPORT_NONE,
    REPORT_REPORTEES,
    VIEW_ALL_LEADS,
    VIEW_ALL_USERS,
    VIEW_REPORTEES,
    VIEW_LEAD_SOURCE,
    VIEW_UNASSIGNED_LEADS,
    cached,
)
from app.schemas.global_settings import GlobalSettings
from app.schemas.lead import (
    Lead,
    LeadCounts,
    LeadFilters,
    LeadHistoryPage,
    LeadPage,
)
from app.schemas.report import ReportFilters, ReportPage
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
        page = get_all_leads(self._http, self._scoped(LeadFilters(lead_ids=[lead_id])), page_size=1)
        if not page.leads:
            raise LeadNotFoundError(f"Lead '{lead_id}' not found")
        return self._redact_sources(page.leads)[0]

    # ---------------------------------------------------------- caller identity

    def my_user_id(self) -> str | None:
        """The caller's own user GUID.

        Tokens differ by tenant: some carry the GUID in a claim, others carry
        only a login name. A name is useless to the API - every user field is
        typed System.Guid - so it is looked up in the user directory once per
        request and cached.
        """
        return cached("my_user_id", self._resolve_my_user_id)

    def _resolve_my_user_id(self) -> str | None:
        if not self._jwt:
            return None

        my_id = jwt_user_id(self._jwt)
        if my_id:
            return my_id

        login = jwt_user_name(self._jwt)
        if not login:
            log.warning("The caller's JWT carries neither a user id nor a name")
            return None

        handle = login.split("@")[0].strip().lower()
        for user in self.list_users():
            names = {
                (user.user_name or "").strip().lower(),
                f"{user.first_name or ''} {user.last_name or ''}".strip().lower(),
            }
            if handle in names:
                log.info("Resolved the caller to %s via the user directory", user.user_name)
                return user.id

        log.warning("No user in the directory matches the caller '%s'", login)
        return None

    # ---------------------------------------------------- permissions & tenant

    def my_permissions(self) -> set[str]:
        """The caller's flat permission set; empty when it cannot be read.

        Empty means "assume nothing extra is allowed", which is the safe
        direction: the caller still sees their own leads, just not everyone's.
        """
        return cached("my_permissions", self._fetch_permissions)

    def _fetch_permissions(self) -> set[str]:
        my_id = self.my_user_id()
        if not my_id:
            return set()
        try:
            return get_user_permissions(self._http, my_id)
        except CRMError as exc:
            log.warning("Could not read the caller's permissions (%s) - assuming none", exc)
            return set()

    def can_access_all_leads(self) -> bool:
        return VIEW_ALL_LEADS in self.my_permissions()

    def can_view_lead_source(self) -> bool:
        return VIEW_LEAD_SOURCE in self.my_permissions()

    def can_view_unassigned_leads(self) -> bool:
        return VIEW_UNASSIGNED_LEADS in self.my_permissions()

    def report_permission(self) -> int:
        """How wide a report this caller may run: all users, reportees, or none.

        Every report body carries this, and it is never user-supplied - the
        model cannot widen its own scope by asking.
        """
        permissions = self.my_permissions()
        if VIEW_ALL_USERS in permissions:
            return REPORT_ALL_USERS
        if VIEW_REPORTEES in permissions:
            return REPORT_REPORTEES
        return REPORT_NONE

    def uses_custom_status(self) -> bool:
        """Whether this tenant's leads live behind the custom-filters endpoints.

        Read from the tenant's own IsCustomStatusEnabled setting, exactly as
        Leadrat's MCP server routes. A setting we cannot read falls back to
        False, which keeps the previous behaviour (try new/all, fall back).
        """
        return cached("custom_status", self._fetch_custom_status)

    def _fetch_custom_status(self) -> bool:
        try:
            settings = get_global_settings(self._http)
        except CRMError as exc:
            log.warning("Could not read global settings (%s) - assuming standard status", exc)
            return False
        return bool(settings and settings.is_custom_status_enabled)

    # ------------------------------------------------------- permission gates

    UNASSIGNED_VISIBILITY = 3  # LeadVisibility.UnassignLead

    SOURCE_DENIED = (
        "You do not have permission to filter leads by source or sub-source."
    )
    UNASSIGNED_DENIED = "You do not have permission to view unassigned leads."
    SOURCE_REDACTED = "Hidden - you do not have permission to view lead sources."

    def _check_lead_access(self, filters: LeadFilters) -> None:
        """Refuse what the caller's role does not allow, before asking the CRM.

        Leadrat enforces this itself, but a refusal explaining which permission
        is missing is worth far more to the user than whatever the backend
        returns for a request it will not answer - and it saves the round trip.
        """
        wants_source = bool(filters.source_codes or filters.source or filters.sub_sources)
        if wants_source and not self.can_view_lead_source():
            raise CRMError(self.SOURCE_DENIED)

        wants_unassigned = filters.lead_visibility == self.UNASSIGNED_VISIBILITY
        if wants_unassigned and not self.can_view_unassigned_leads():
            raise CRMError(self.UNASSIGNED_DENIED)

    def _scoped(self, filters: LeadFilters) -> LeadFilters:
        """The same filters, carrying the caller's real lead-access scope."""
        self._check_lead_access(filters)
        return filters.model_copy(update={"can_access_all_leads": self.can_access_all_leads()})

    def _redact_sources(self, leads: list[Lead]) -> list[Lead]:
        """Blank each lead's source for a caller not allowed to see it.

        A field-level permission: the leads themselves are still theirs to see,
        so the answer is redacted rather than refused.
        """
        if self.can_view_lead_source():
            return leads
        log.info("Redacting the source on %d lead(s) - caller lacks the permission", len(leads))
        return [
            lead.model_copy(update={"source": self.SOURCE_REDACTED, "sub_source": None})
            for lead in leads
        ]

    # ------------------------------------------------------------------ leads

    def search_leads(self, filters: LeadFilters) -> LeadPage:
        """Search the endpoint this tenant actually keeps its leads behind.

        Which one that is comes from IsCustomStatusEnabled rather than from
        trying one and retrying the failure: the retry cost a round trip on
        every call and could only ever work when the wrong endpoint failed
        loudly. The retry is kept as a fallback for the case where the setting
        is unreadable and the guess turns out wrong.
        """
        filters = self._scoped(filters)
        if self.uses_custom_status():
            page = get_leads_custom_filters(
                self._http, filters, page=filters.page, page_size=filters.limit
            )
        else:
            try:
                page = get_all_leads(self._http, filters, page=filters.page, page_size=filters.limit)
            except CRMError as exc:
                log.warning("search_leads: /lead/new/all failed (%s), retrying via custom-filters", exc)
                page = get_leads_custom_filters(
                    self._http, filters, page=filters.page, page_size=filters.limit
                )
        return page.model_copy(update={"leads": self._redact_sources(page.leads)})

    def get_lead_counts(self, filters: LeadFilters) -> LeadCounts:
        """Up to three independent count breakdowns for one filter, matching
        old mcp's single get_lead_counts tool: per-status counts, generic
        base-filter totals, and (when the tenant has it) active-pipeline
        totals.
        """
        filters = self._scoped(filters)
        if self.uses_custom_status():
            status_counts = get_leads_custom_filters_count(self._http, filters)
        else:
            try:
                status_counts = get_lead_status_counts(self._http, filters)
            except CRMError as exc:
                log.warning(
                    "get_lead_counts: /lead/counts/statuses failed (%s), retrying via custom-filters", exc
                )
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


    # ---------------------------------------------------------------- reports

    # Reports that come as a pair: the same body, one endpoint per tenant shape.
    _REPORT_PATHS: dict[str, tuple[str, str | None]] = {
        "user_status": ("/report/user/new/status", "/report/user/status/custom"),
        "project_status": ("/report/project/status/new", "/report/project/status/custom"),
        "source_status": ("/report/source/status/new", "/report/source/status/custom"),
        "subsource_status": ("/report/subsource/status/new", "/report/subsource/status/custom"),
        # Single-endpoint reports: the same shape for every tenant.
        "country_status": ("/report/country/status", None),
        "user_substatus": ("/report/substatus", None),
        "campaign_substatus": ("/report/campaign/bysubstatus", None),
        "channel_partner_substatus": ("/report/channelpartner/bysubstatus", None),
        "user_source": ("/report/uservssource", None),
        "user_subsource": ("/report/uservssubsource", None),
        "revenue_source": ("/report/revenue/uservssource/by-source", None),
        "revenue_subsource": ("/report/revenue/uservssource/by-subsource", None),
        "call_log": ("/report/user/call-log/new", None),
    }

    # The activity report is four calls, not one: each level returns the same
    # users with a different slice of counts, merged per user by the caller.
    _ACTIVITY_LEVELS: dict[str, str] = {
        "schedule": "/report/activity/level9",
        "edits": "/report/activity/level10",
        "communication": "/report/activity/level11",
        "meetings": "/report/activity/level12",
    }

    REPORT_DENIED = (
        "You do not have permission to run reports "
        "(needs Reports.ViewAllUsers or Reports.ViewReportees)."
    )

    def _report_filters(self, filters: ReportFilters) -> ReportFilters:
        """Stamp the caller's own report scope onto the request.

        A caller with neither report permission never reaches the API: the
        backend would answer them nothing useful anyway, and saying which
        permission is missing is more use than an empty report.
        """
        scope = self.report_permission()
        if scope == REPORT_NONE:
            raise CRMError(self.REPORT_DENIED)
        return filters.model_copy(update={"report_permission": scope})

    def run_report(self, report: str, filters: ReportFilters) -> ReportPage:
        """One report by name, on the endpoint this tenant answers it from."""
        paths = self._REPORT_PATHS.get(report)
        if paths is None:
            raise CRMError(f"Unknown report '{report}'")

        default_path, custom_path = paths
        use_custom = bool(custom_path) and self.uses_custom_status()
        path = custom_path if use_custom else default_path
        return run_report(self._http, path, self._report_filters(filters), use_custom)

    def get_activity_report(self, filters: ReportFilters) -> ReportPage:
        """The activity report: four count slices merged into one row per user.

        Each level answers with the same users, so they are merged on the user
        rather than returned as four reports the model would have to line up
        itself.
        """
        scoped = self._report_filters(filters)
        merged: dict[str, dict] = {}
        order: list[str] = []
        total: int | None = None

        for level, path in self._ACTIVITY_LEVELS.items():
            try:
                page = run_report(self._http, path, scoped)
            except CRMError as exc:
                log.warning("activity report: %s unavailable (%s)", level, exc)
                continue
            total = total if total is not None else page.total
            for row in page.rows:
                key = str(row.get("userId") or row.get("id") or row.get("userName") or len(order))
                if key not in merged:
                    merged[key] = {}
                    order.append(key)
                merged[key].update(row)

        return ReportPage(
            rows=[merged[key] for key in order],
            total=total if total is not None else len(order),
            page=scoped.page,
            page_size=scoped.limit,
        )

    def get_call_report(self, filters: ReportFilters) -> ReportPage:
        return self.run_report("call_log", filters)

    def get_lead_history(self, lead_id: str, limit: int = 20) -> LeadHistoryPage:
        return get_lead_history(self._http, lead_id, page_size=limit)

    def get_user_profile(self, user_id: str) -> UserProfile:
        profile = get_user_profile(self._http, user_id)
        if not profile.user_id:
            raise UserNotFoundError(f"User '{user_id}' not found")
        return profile

    def get_my_profile(self) -> UserProfile:
        my_id = self.my_user_id()
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
