"""Lead domain models, shaped after the Leadrat lead-search response.

The filter surface here mirrors the Leadrat MCP server's (old mcp) LeadTools:
every field below was confirmed against the live Swagger schema for
GetAllLeadsOnlyByNewFiltersRequest (and its five sibling request DTOs, which
are byte-for-byte the same 229-field shape) at
https://connect.leadrat.info/swagger/v1/swagger.json - see
`integrations/crm/leadrat/endpoints/get_all_leads.py` for the wire mapping.
"""

from pydantic import BaseModel


class Lead(BaseModel):
    id: str
    name: str
    phone: str | None = None
    email: str | None = None
    source: str | None = None
    sub_source: str | None = None
    status: str | None = None
    location: str | None = None
    project: str | None = None
    requirement: str | None = None
    assigned_to: str | None = None
    lead_number: str | None = None
    scheduled_at: str | None = None
    created_at: str | None = None
    last_modified_at: str | None = None


class LeadPage(BaseModel):
    """One page of leads plus how many matched in total."""

    total: int | None = None
    leads: list[Lead] = []


class LeadHistoryEntry(BaseModel):
    """One field-change audit entry on a lead, from Leadrat's
    GET /lead/histories/{id} (confirmed against the live Swagger spec -
    see `integrations/crm/leadrat/endpoints/get_lead_history.py`).
    """

    field_name: str | None = None  # which field changed, e.g. "Status"
    category: str | None = None  # filterKey: None, Assignment, Notes, Status
    old_value: str | None = None
    new_value: str | None = None
    updated_by: str | None = None
    updated_at: str | None = None
    action_type: str | None = None  # e.g. Create, Update


class LeadHistoryPage(BaseModel):
    """One page of a lead's history plus how many entries exist in total.

    Leadrat doesn't page this endpoint server-side - `total` is the full
    count and paging is applied client-side in get_lead_history.py.
    """

    total: int | None = None
    entries: list[LeadHistoryEntry] = []


class LeadDateFilter(BaseModel):
    """One date-field condition, sent inside the wire "dates" list so a
    single search can combine several date fields (e.g. created on X AND
    modified between Y and Z) in one call.

    date_type is the Leadrat LeadDateType code: 0=All, 1=ReceivedDate,
    2=ScheduledDate, 3=ModifiedDate, 4=DeletedDate, 5=PossessionDate,
    6=PickedDate, 7=BookedDate, 8=AssignedDate, 9=ReEnquiredDate.
    """

    date_type: int
    from_date: str
    to_date: str


class LeadFilters(BaseModel):
    """What the agent may filter leads on.

    Maps onto the Leadrat request body in
    `integrations/crm/leadrat/endpoints/get_all_leads.py`. Two kinds of
    field live here: plain pass-through values (free text, numbers, lists
    of names) that Leadrat accepts as-is, and *_ids/*_codes fields that the
    tool layer has already resolved from the user's words (names -> GUIDs,
    labels -> Leadrat's integer enum codes) before building this model -
    see `agent/tools/lead/_resolvers.py`.
    """

    # Sent on every lead request. Whether the caller may see the whole tenant's
    # leads is the backend's decision, derived from their role permissions -
    # the agent never sets it, and it is not a filter the user can ask for.
    can_access_all_leads: bool = False

    # free text / pagination
    keyword: str | None = None
    limit: int = 10
    page: int = 1

    # legacy single-value convenience, still used by get_lead's id lookup
    # and kept so older call sites keep working
    location: str | None = None
    source: str | None = None
    status: str | None = None

    # identity lookups
    lead_ids: list[str] | None = None

    # already-resolved ids (filled in by the tool layer after name resolution)
    status_ids: list[str] | None = None
    sub_status_ids: list[str] | None = None
    assigned_to_ids: list[str] | None = None  # wire: assignTo
    secondary_user_ids: list[str] | None = None  # wire: secondaryUsers
    property_type_ids: list[str] | None = None  # wire: propertyType
    property_sub_type_ids: list[str] | None = None  # wire: propertySubType

    # enums, already resolved to Leadrat's integer codes
    filter_type: int | None = None  # LeadFilterTypeWeb
    lead_visibility: int | None = None  # BaseLeadVisibility
    owner_selection: int | None = None  # OwnerSelectionType
    lead_tags: list[int] | None = None  # LeadTagEnum
    source_codes: list[int] | None = None  # LeadSource - list form; supersedes `source` when set
    bhk_type_codes: list[int] | None = None  # BHKType
    purpose_codes: list[int] | None = None  # Purpose
    offer_type_codes: list[int] | None = None  # OfferType
    furnished_codes: list[int] | None = None  # FurnishStatus
    profession_codes: list[int] | None = None  # Profession
    meeting_or_visit_status_codes: list[int] | None = None  # MeetingOrVisitCompletionStatus

    # multiple date-field conditions in one call (wire: "dates")
    date_filters: list[LeadDateFilter] | None = None

    # plain pass-through filters, no resolution needed
    min_budget: int | None = None
    max_budget: int | None = None
    beds: list[int] | None = None
    baths: list[int] | None = None
    no_of_bhks: list[float] | None = None
    cities: list[str] | None = None
    states: list[str] | None = None
    countries: list[str] | None = None
    zones: list[str] | None = None
    locations: list[str] | None = None  # micro-locations, distinct from `cities`
    projects: list[str] | None = None
    sub_sources: list[str] | None = None
    company_name: str | None = None
    referral_name: str | None = None
    is_with_team: bool | None = None
    campaign_names: list[str] | None = None
    utm_sources: list[str] | None = None


class LeadStatusCount(BaseModel):
    """One status's (or sub-status's) lead count, from the custom-filters-count API."""

    name: str | None = None
    count: int = 0
    sub_status_counts: list["LeadStatusCount"] | None = None


class LeadBaseFilterCounts(BaseModel):
    """Generic base-filter lead counts, from POST /lead/new/counts/basefilter."""

    all_leads_count: int = 0
    my_leads_count: int = 0
    team_leads_count: int = 0
    unassign_leads_count: int | None = None
    deleted_leads_count: int = 0
    duplicate_leads_count: int = 0
    re_enquired_leads_count: int = 0
    pending_assignment_leads_count: int = 0


class LeadActiveCounts(BaseModel):
    """Active-pipeline lead counts, from POST /lead/counts/active (regular tenants only).

    Every field is nullable on the wire - the backend leaves buckets it did
    not compute as null.
    """

    active_leads_count: int | None = None
    new_leads_count: int | None = None
    pending_leads_count: int | None = None
    scheduled_leads_count: int | None = None
    overdue_leads_count: int | None = None
    booked_leads_count: int | None = None
    scheduled_today_leads_count: int | None = None
    scheduled_tomorrow_leads_count: int | None = None
    scheduled_next_two_days_leads_count: int | None = None
    upcoming_scheduled_leads_count: int | None = None
    site_visits_count: int | None = None
    meetings_count: int | None = None
    callback_count: int | None = None
    all_leads_count: int | None = None
    overdue_meeting_count: int | None = None
    overdue_site_visit_count: int | None = None
    overdue_callback_count: int | None = None
    booking_cancel_lead_count: int | None = None
    expression_of_interest_lead_count: int | None = None
    invoiced_leads_count: int | None = None
    pool_leads_count: int | None = None


class LeadCounts(BaseModel):
    """The combined result of get_lead_counts: up to three independent
    count breakdowns for the same filter, matching old mcp's single
    get_lead_counts tool. status_counts comes from whichever of the two
    per-tenant status-count endpoints answered (regular-tenant
    /lead/counts/statuses, or custom-status-tenant
    /lead/custom-filters-count-level1) - the caller never needs to know
    which. active_counts is only present for some tenants.
    """

    status_counts: list[LeadStatusCount] = []
    base_filter_counts: LeadBaseFilterCounts | None = None
    active_counts: LeadActiveCounts | None = None
