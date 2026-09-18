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
# Mirrors the fields old mcp lifts to the top level of its LeadResponse - in
# particular source AND sub_source, since a nested lead field (the enquiry's
# sub-source, a status's sub-status) is a lead field like any other and the
# user can ask about it directly.
SAMPLE_FIELDS = (
    "id",
    "name",
    "phone",
    "email",
    "source",
    "sub_source",
    "status",
    "location",
    "project",
    "requirement",
    "assigned_to",
    "scheduled_at",
)


def _compact(lead: Lead) -> dict:
    data = lead.model_dump()
    return {key: data[key] for key in SAMPLE_FIELDS if data.get(key)}


@tool
def search_leads(
    keyword: str = "",
    limit: int = 10,
    page: int = 1,
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
    """List or search the user's leads. No arguments = the user's leads overall
    ("show my leads", "all leads"). Returns the total match count plus a sample.

    keyword: name, email or phone. limit: 1-15 leads to sample. page: 1-based,
      for "show me the next ones" after a first call.
    A lead's nested fields are lead fields too: sub_source (under the enquiry)
    and the sub-status (under status) can be asked about and filtered on.
    filter_type: All|New|Today|Overdue|NotInterested|Dropped|Escalated|Pending|
      Booked|Upcoming|BookingCancel
    lead_visibility: SelfWithReportee(default)|Self|Reportee|UnassignLead|
      DeletedLeads|DuplicateLeads|ReEnquired|PendingAssignment|LeadPool
    lead_tags: Hot|Warm|Cold|Escalated|AboutToConvert|Highlighted
    date_filters: list of {"date_type","from_date","to_date"}; put EVERY date
      condition in this one list. date_type: All|ReceivedDate("created")|
      ScheduledDate|ModifiedDate("updated")|DeletedDate|PossessionDate|
      PickedDate|BookedDate|AssignedDate|ReEnquiredDate.
      from_date/to_date take an ISO date (2026-09-18) OR a relative phrase,
      which the server resolves against its own clock: "today", "yesterday",
      "tomorrow", "this week", "last week", "this month", "last month",
      "this year", "last 7 days", "last 30 days", "last 90 days". Put the same
      phrase in both ends for a span ("this week" -> Monday..today) or the same
      date in both for a single day. Never ask the user which format to use.
    min_budget, max_budget: currency units (50 lakhs = 5000000).
    assigned_to_names: owner names or ["me"], matched case-insensitively. Two
      names joined by "or" ("leads of Darshan or Priya") both go here with
      owner_selection="Both". owner_selection: Both(default for any generic
      "whose leads" ask)|PrimaryOwner|SecondaryOwner - set it whenever
      assigned_to_names is given and secondary_user_names is empty.
      secondary_user_names: ONLY when the user wants primary owner X AND
      secondary owner Y, two different people; then leave owner_selection empty.
    status_names, sub_status_names, property_type_names,
      property_sub_type_names: tenant-configured names - check the list_* tools.
    cities, states, countries, zones, locations (micro-locations), projects.
    sources: Facebook, LinkedIn, GoogleAds, Referral, WalkIn, Website, WhatsApp,
      ChannelPartner, PropertyFinder, Bayut, Dubizzle, Microsite (both microsite
      kinds; use PropertyMicrosite/ProjectMicrosite only if named), and more.
      sub_sources: free text.
    beds, baths: [2,3]. no_of_bhks: [1.0,2.5]. bhk_types: Simplex|Duplex|
      PentHouse|Others.
    purposes: Investment|SelfUse. offer_types: Ready|OffPlan|Secondary.
    furnished: Furnished|Semifurnished|Unfurnished.
    professions: Salaried|Business|SelfEmployed|Doctor|Retired|Housewife|
      Student|Unemployed|Others.
    meeting_or_visit_statuses: IsMeetingDone|IsMeetingNotDone|IsSiteVisitDone|
      IsSiteVisitNotDone.
    company_name, referral_name, campaign_names, utm_sources.
    is_with_team: true to include the team's leads.
    """
    filters = build_lead_filters(
        keyword=keyword,
        limit=max(1, min(limit, MAX_LEADS)),
        page=page,
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
    result = get_crm_client().search_leads(filters)

    return json.dumps(
        {
            "total_matching_leads": result.total,
            "page": page,
            "showing": len(result.leads),
            "leads": [_compact(lead) for lead in result.leads],
        },
        default=str,
    )
