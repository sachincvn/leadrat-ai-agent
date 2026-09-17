"""Tool: list or search leads.

Backed by POST /lead/new/all (or /lead/custom-filters for a custom-lead-
status tenant - the client picks automatically, see LeadratClient.search_leads).

The tenant can hold six figures of leads, so the tool never hands the model a
large page: it returns the total match count plus a small sample with only the
fields worth reasoning about. A bigger page would blow the model's context and
the inference API would reject the request outright.

The parameter surface mirrors old mcp's search_leads tool as closely as the
underlying data allows - see `_resolvers.py` for how names/labels are turned
into the GUIDs and enum codes Leadrat expects.
"""

import json

from langchain_core.tools import tool

from app.agent.tools.lead._resolvers import build_lead_filters
from app.integrations.crm.factory import get_crm_client
from app.schemas.lead import Lead

MAX_LEADS = 15
SAMPLE_FIELDS = ("id", "name", "phone", "source", "status", "location", "project", "assigned_to")


def _compact(lead: Lead) -> dict:
    data = lead.model_dump()
    return {key: data[key] for key in SAMPLE_FIELDS if data.get(key)}


@tool
def search_leads(
    keyword: str = "",
    limit: int = 10,
    filter_type: str = "",
    lead_visibility: str = "",
    lead_tags: list[str] | None = None,
    date_filters: list[dict] | None = None,
    min_budget: int | None = None,
    max_budget: int | None = None,
    assigned_to_names: list[str] | None = None,
    owner_selection: str = "",
    secondary_user_names: list[str] | None = None,
    status_names: list[str] | None = None,
    sub_status_names: list[str] | None = None,
    property_type_names: list[str] | None = None,
    property_sub_type_names: list[str] | None = None,
    cities: list[str] | None = None,
    states: list[str] | None = None,
    countries: list[str] | None = None,
    zones: list[str] | None = None,
    locations: list[str] | None = None,
    projects: list[str] | None = None,
    sources: list[str] | None = None,
    sub_sources: list[str] | None = None,
    beds: list[int] | None = None,
    baths: list[int] | None = None,
    no_of_bhks: list[float] | None = None,
    bhk_types: list[str] | None = None,
    purposes: list[str] | None = None,
    offer_types: list[str] | None = None,
    furnished: list[str] | None = None,
    professions: list[str] | None = None,
    meeting_or_visit_statuses: list[str] | None = None,
    company_name: str = "",
    referral_name: str = "",
    is_with_team: bool | None = None,
    campaign_names: list[str] | None = None,
    utm_sources: list[str] | None = None,
) -> str:
    """List or search the user's leads in the CRM.

    Call with no arguments for an overview of the user's leads - that is the
    right call for "show my leads", "get all leads" or "how many leads do I have".
    The result reports the total number of matching leads and a sample of them.

    keyword          - a name, email or phone number to search for
    limit            - how many leads to sample, 1 to 15

    filter_type      - pipeline view. Values: All, New, Today, Overdue,
                       NotInterested, Dropped, Escalated, Pending, Booked,
                       Upcoming, BookingCancel
    lead_visibility  - visibility scope. Values: SelfWithReportee (default),
                       Self, Reportee, UnassignLead, DeletedLeads,
                       DuplicateLeads, ReEnquired, PendingAssignment, LeadPool
    lead_tags        - priority tags. Values: Hot, Warm, Cold, Escalated,
                       AboutToConvert, Highlighted

    date_filters     - list of {"date_type", "from_date", "to_date"} (ISO
                       dates). Put every date condition the user mentioned in
                       this ONE list and make a single call - never call this
                       tool once per date field. date_type values: All,
                       ReceivedDate, ScheduledDate, ModifiedDate, DeletedDate,
                       PossessionDate, PickedDate, BookedDate, AssignedDate,
                       ReEnquiredDate ("created"/"received" -> ReceivedDate,
                       "modified"/"updated" -> ModifiedDate). Use the same
                       date for from_date/to_date for a single day.

    min_budget       - minimum budget in currency units (e.g. 5000000 for 50 lakhs)
    max_budget       - maximum budget in currency units

    assigned_to_names   - owner/assigned-user names, e.g. ["Priya"] or ["me"].
                          Leadrat leads have a PRIMARY and a SECONDARY owner;
                          pair this with owner_selection to say which slot to
                          match. Use owner_selection="Both" for any generic
                          ownership ask ("my leads", "leads assigned to me",
                          "Priya's leads").
    owner_selection     - "Both" (default for a generic ask), "PrimaryOwner",
                          or "SecondaryOwner". Leave empty only when
                          assigned_to_names and secondary_user_names name
                          DIFFERENT people for the two roles at once.
    secondary_user_names - secondary-owner names. Only for the case above
                          (primary owner X AND secondary owner Y, different
                          people) - leave empty otherwise.

    status_names        - lead status names, e.g. ["New", "Pending"]. Use
                          list_statuses to see the tenant's real values first.
    sub_status_names     - sub-status names, e.g. ["Callback Scheduled"].
    property_type_names  - property type names, e.g. ["Apartment", "Villa"].
                          Use list_property_types first.
    property_sub_type_names - property sub-type names, e.g. ["2BHK Apartment"].

    cities, states, countries, zones - geography filters (lists)
    locations            - micro-locations, e.g. ["Andheri", "Bandra"]
    projects              - project names (list)

    sources               - lead sources (list). E.g. Facebook, LinkedIn,
                          GoogleAds, Referral, WalkIn, Website, WhatsApp,
                          ChannelPartner, PropertyFinder, Bayut, Dubizzle,
                          Microsite (matches BOTH property and project
                          microsites - use PropertyMicrosite/ProjectMicrosite
                          only when the user names that specific one), and more.
    sub_sources           - free-text sub-source values (list)

    beds, baths           - bedroom/bathroom counts (lists), e.g. [2, 3]
    no_of_bhks            - BHK count as decimals (list), e.g. [1.0, 2.5]
    bhk_types             - BHK configuration. Values: Simplex, Duplex, PentHouse, Others

    purposes              - Values: Investment, SelfUse
    offer_types           - Values: Ready, OffPlan, Secondary
    furnished             - Values: Furnished, Semifurnished, Unfurnished
    professions           - Values: Salaried, Business, SelfEmployed, Doctor,
                          Retired, Housewife, Student, Unemployed, Others
    meeting_or_visit_statuses - Values: IsMeetingDone, IsMeetingNotDone,
                          IsSiteVisitDone, IsSiteVisitNotDone

    company_name          - e.g. "Tata Consultancy"
    referral_name          - referral person's name
    is_with_team           - true to also include the user's team's leads
    campaign_names         - campaign names (list)
    utm_sources            - UTM source values (list), e.g. ["google", "facebook"]

    Pass only values the user actually stated - never invent a filter value.
    """
    filters = build_lead_filters(
        keyword=keyword,
        limit=max(1, min(limit, MAX_LEADS)),
        filter_type=filter_type,
        lead_visibility=lead_visibility,
        lead_tags=lead_tags,
        date_filters=date_filters,
        min_budget=min_budget,
        max_budget=max_budget,
        assigned_to_names=assigned_to_names,
        owner_selection=owner_selection,
        secondary_user_names=secondary_user_names,
        status_names=status_names,
        sub_status_names=sub_status_names,
        property_type_names=property_type_names,
        property_sub_type_names=property_sub_type_names,
        cities=cities,
        states=states,
        countries=countries,
        zones=zones,
        locations=locations,
        projects=projects,
        sources=sources,
        sub_sources=sub_sources,
        beds=beds,
        baths=baths,
        no_of_bhks=no_of_bhks,
        bhk_types=bhk_types,
        purposes=purposes,
        offer_types=offer_types,
        furnished=furnished,
        professions=professions,
        meeting_or_visit_statuses=meeting_or_visit_statuses,
        company_name=company_name,
        referral_name=referral_name,
        is_with_team=is_with_team,
        campaign_names=campaign_names,
        utm_sources=utm_sources,
    )
    page = get_crm_client().search_leads(filters)

    return json.dumps(
        {
            "total_matching_leads": page.total,
            "showing": len(page.leads),
            "leads": [_compact(lead) for lead in page.leads],
        },
        default=str,
    )
