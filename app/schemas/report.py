"""Report filters and results.

Leadrat's twelve reports differ in what they group by, not in how they are
asked for: one body shape carries paging, the caller's report scope, a
multi-date filter and a long list of optional lead filters, and each endpoint
answers with rows plus totals.

Rows stay as plain dicts rather than a model per report. The backend ships 74
distinct report DTOs whose columns change per tenant - a custom-status tenant
gets a named-status array where a standard one gets fixed count columns - and
modelling each would freeze a shape that is meant to vary. The agent reads
these rows as names and numbers, so the dict is what it needs; the fields that
must be understood (totals, paging, which tenant shape came back) are typed.
"""

from pydantic import BaseModel

from app.schemas.lead import LeadDateFilter


class ReportFilters(BaseModel):
    """What any report may be narrowed by.

    Every field is optional and omitted from the wire body when unset, so the
    backend applies its own defaults instead of receiving an explicit null.
    """

    # paging
    page: int = 1
    limit: int = 50

    # 0=All, 1=Active, 2=InActive. Active by default, as in the activity report.
    user_status: int = 1

    # Scope, derived from the caller's role permissions - never user-supplied.
    report_permission: int | None = None

    dates: list[LeadDateFilter] | None = None
    user_ids: list[str] | None = None
    search_text: str | None = None

    source_codes: list[int] | None = None
    sub_sources: list[str] | None = None
    # ProjectAvailability: 0=All, 1=Active, 2=Inactive, 3=Deleted.
    project_availability: list[int] | None = None

    cities: list[str] | None = None
    states: list[str] | None = None
    countries: list[str] | None = None
    customer_countries: list[str] | None = None
    projects: list[str] | None = None
    campaign_names: list[str] | None = None

    # Activity window for the meeting/site-visit columns. Independent of
    # `dates`, which filters the leads themselves. The "ForSubSource" wire
    # names are the backend's own, shared verbatim across reports.
    activity_from_date: str | None = None
    activity_to_date: str | None = None


class ReportPage(BaseModel):
    """One page of a report."""

    rows: list[dict] = []
    total: int | None = None
    page: int | None = None
    page_size: int | None = None
    # True when the tenant's custom-status endpoint answered, which changes the
    # shape of each row's status columns.
    custom_status_tenant: bool = False
