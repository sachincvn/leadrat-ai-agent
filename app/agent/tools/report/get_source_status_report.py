"""Tool: Leads per SOURCE broken down by STATUS.

Backed by the shared report request (see endpoints/run_report.py): one body,
the caller's own report scope, and whichever endpoint this tenant answers
from.
"""

from langchain_core.tools import tool

from app.agent.tools.report._shared import run


@tool
def get_source_status_report(
    date_filters: list[dict] | None = None,
    user_names: list[str] | None = None,
    search_text: str = "",
    sources: list[str] | None = None,
    sub_sources: list[str] | None = None,
    cities: list[str] | None = None,
    states: list[str] | None = None,
    countries: list[str] | None = None,
    customer_countries: list[str] | None = None,
    projects: list[str] | None = None,
    campaign_names: list[str] | None = None,
    user_status: str = "",
    activity_from_date: str = "",
    activity_to_date: str = "",
    limit: int = 50,
    page: int = 1,
) -> str:
    """Leads per SOURCE broken down by STATUS - how each channel is converting.

    Returns one row per source, with the counts as the CRM reports them -
    column names vary by tenant, so read them from the row rather than assuming.

    Filters (all optional):
        date_filters: list of {"date_type","from_date","to_date"}; filters which
          LEADS are counted. Relative words ("today", "this month") are resolved
          against the server's clock.
        user_names: report on these users only; ["me"] for the caller.
        search_text: partial user name - narrows which rows come back.
        sources: lead sources by name (Facebook, Website, ...).
        sub_sources, cities, states, countries, customer_countries, projects,
          campaign_names: free-text filters, matched as given.
        user_status: All|Active(default)|InActive.
        activity_from_date, activity_to_date: ISO dates scoping the meeting and
          site-visit columns, independent of date_filters.
        limit, page: paging; up to 500 rows a page.
    """
    return run(
        "source_status",
        date_filters=date_filters,
        user_names=user_names,
        search_text=search_text,
        sources=sources,
        sub_sources=sub_sources,
        cities=cities,
        states=states,
        countries=countries,
        customer_countries=customer_countries,
        projects=projects,
        campaign_names=campaign_names,
        user_status=user_status,
        activity_from_date=activity_from_date,
        activity_to_date=activity_to_date,
        limit=limit,
        page=page,
    )
