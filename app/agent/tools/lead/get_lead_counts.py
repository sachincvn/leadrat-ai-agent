"""Tool: lead COUNTS (aggregate numbers), without fetching lead records.

Combines three of Leadrat's count endpoints into one call - per-status
counts (from whichever of /lead/counts/statuses or
/lead/custom-filters-count-level1 applies to this tenant), generic
base-filter totals (/lead/new/counts/basefilter), and, where available,
active-pipeline totals (/lead/counts/active) - see
LeadratClient.get_lead_counts. This mirrors old mcp's single get_lead_counts
tool, which returns the same three blocks from one call instead of making
the model pick between several narrower count tools.

Takes the identical filter surface as search_leads (built the same way, via
_resolvers.build_lead_filters) so counting and listing the same slice of
leads never drift apart.
"""

import json

from langchain_core.tools import tool

from app.agent.tools.lead._resolvers import build_lead_filters
from app.integrations.crm.factory import get_crm_client


@tool
def get_lead_counts(
    keyword: str = "",
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
    """Get lead COUNTS (aggregate numbers) for a given filter, WITHOUT
    fetching the lead records themselves.

    Use this instead of search_leads whenever the user only wants a count /
    "how many" (e.g. "how many hot leads", "how many leads created today",
    "count of leads in New status"), never to enumerate the leads themselves.

    Accepts exactly the same filters as search_leads - see that tool's
    docstring for what each one means and its accepted values.

    Returns up to three blocks:
    - status_counts: a per-status breakdown, each entry with a name, a
      count, and nested sub_status_counts.
    - base_filter_counts: generic totals - all_leads_count, my_leads_count,
      team_leads_count, unassign_leads_count, deleted_leads_count,
      duplicate_leads_count, re_enquired_leads_count,
      pending_assignment_leads_count.
    - active_counts: active-pipeline totals (new_leads_count,
      overdue_leads_count, booked_leads_count, and more) - present only for
      some tenants; when absent (null), derive an active-pipeline number
      from status_counts/base_filter_counts instead.

    Read the matching name/field from the result and report only the
    count(s) the user asked for - never enumerate every bucket back to them.
    """
    filters = build_lead_filters(
        keyword=keyword,
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
    counts = get_crm_client().get_lead_counts(filters)
    return counts.model_dump_json(exclude_none=True)
