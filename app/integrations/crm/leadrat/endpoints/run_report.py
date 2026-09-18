"""The one request every Leadrat report is made with.

Twelve reports, one body: paging, the caller's report scope, the shared
multi-date filter and whichever lead filters were given. Several of them come
as a pair of endpoints - a default one and a custom-status one - taking a
byte-for-byte identical request and differing only in the response, so the pair
is passed in and the tenant setting picks between them.
"""

from typing import Any

from app.core.clock import to_utc_instant
from app.core.logging import get_logger
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.report import ReportFilters, ReportPage

log = get_logger(__name__)

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500

# Where a report's rows may be found. The backend names the collection after
# whatever the report groups by, so the first list wins rather than one key.
_ROW_KEYS = (
    "users", "items", "rows", "sources", "subSources", "projects",
    "countries", "campaigns", "channelPartners", "data", "result",
)


def build_body(filters: ReportFilters) -> dict[str, Any]:
    """Translate ReportFilters into the shared report request body."""
    body: dict[str, Any] = {
        "pageNumber": max(filters.page, 1),
        "pageSize": min(filters.limit if filters.limit > 0 else DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE),
        "userStatus": filters.user_status,
    }

    # Scope is the backend's decision, not the caller's; it is always sent.
    if filters.report_permission is not None:
        body["reportPermission"] = filters.report_permission

    if filters.dates:
        # Same wire shape, and the same time-zone rule, as lead search.
        body["dates"] = [
            {
                "multiDateType": d.date_type,
                "multiFromDate": to_utc_instant(d.from_date),
                "multiToDate": to_utc_instant(d.to_date),
            }
            for d in filters.dates
        ]

    optional: dict[str, Any] = {
        "userIds": filters.user_ids,
        "searchText": filters.search_text,
        "sources": filters.source_codes,
        "subSources": filters.sub_sources,
        "projectAvailability": filters.project_availability,
        "cities": filters.cities,
        "states": filters.states,
        "countries": filters.countries,
        "customerCountries": filters.customer_countries,
        "projects": filters.projects,
        "campaignNames": filters.campaign_names,
        "fromDateForSubSource": filters.activity_from_date,
        "toDateForSubSource": filters.activity_to_date,
    }
    body.update({key: value for key, value in optional.items() if value})
    return body


def extract_rows(payload: Any) -> list[dict]:
    """The report's rows, whatever the backend named the collection.

    A report that groups by user calls them "users", one that groups by source
    "sources", and so on - there is no single key to read, so the first list of
    objects found under a known name is taken.
    """
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []

    data = payload.get("data") if isinstance(payload.get("data"), (dict, list)) else payload
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]

    for key in _ROW_KEYS:
        value = data.get(key) if isinstance(data, dict) else None
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]

    log.warning(
        "Unrecognised report envelope. Keys: %s",
        list(data) if isinstance(data, dict) else type(data).__name__,
    )
    return []


def _int(payload: Any, *keys: str) -> int | None:
    source = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else payload
    if not isinstance(source, dict):
        return None
    for key in keys:
        value = source.get(key)
        if isinstance(value, int):
            return value
    return None


def run_report(
    http: LeadratHttp,
    path: str,
    filters: ReportFilters,
    custom_status_tenant: bool = False,
) -> ReportPage:
    """POST one report and return its rows with whatever totals came back."""
    payload = http.post(path, build_body(filters))
    rows = extract_rows(payload)
    log.info("report %s -> %d row(s)", path, len(rows))
    return ReportPage(
        rows=rows,
        total=_int(payload, "totalCount", "userCount", "count"),
        page=_int(payload, "pageNumber"),
        page_size=_int(payload, "pageSize"),
        custom_status_tenant=custom_status_tenant,
    )
