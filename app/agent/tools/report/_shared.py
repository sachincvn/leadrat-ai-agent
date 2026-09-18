"""The filter surface every report tool shares, resolved once.

The twelve reports differ in what they group by, not in what they can be
narrowed by, so the argument list and its resolution live here: names in,
tenant ids and enum codes out, exactly as the lead tools do it.
"""

import json

from app.agent.tools.lead._resolvers import (
    parse_date_filters,
    resolve_source_codes,
    resolve_user_ids,
)
from app.integrations.crm.factory import get_crm_client
from app.schemas.report import ReportFilters

# What every report tool's docstring says about its filters, kept in one place
# so twelve tool descriptions cannot drift apart.
FILTER_DOC = """    date_filters: list of {"date_type","from_date","to_date"}; filters which
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
    limit, page: paging; up to 500 rows a page."""

USER_STATUS: dict[str, int] = {"all": 0, "active": 1, "inactive": 2}


def build_report_filters(
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
) -> ReportFilters:
    return ReportFilters(
        page=max(1, page),
        limit=max(1, min(limit, 500)),
        user_status=USER_STATUS.get(user_status.strip().lower(), 1),
        dates=parse_date_filters(date_filters),
        user_ids=resolve_user_ids(user_names),
        search_text=search_text or None,
        source_codes=resolve_source_codes(sources),
        sub_sources=sub_sources or None,
        cities=cities or None,
        states=states or None,
        countries=countries or None,
        customer_countries=customer_countries or None,
        projects=projects or None,
        campaign_names=campaign_names or None,
        activity_from_date=activity_from_date or None,
        activity_to_date=activity_to_date or None,
    )


def run(report: str, **kwargs) -> str:
    """Run one named report and hand the model its rows as JSON."""
    filters = build_report_filters(**kwargs)
    client = get_crm_client()
    page = (
        client.get_activity_report(filters)
        if report == "activity"
        else client.run_report(report, filters)
    )
    return json.dumps(page.model_dump(), default=str)
