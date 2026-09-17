"""POST /lead/custom-filters - lead search for custom-status tenants.

Same request body and response shape as POST /lead/new/all (see get_all_leads);
only the path differs, so this reuses its body-building and row-mapping.
"""

from app.core.logging import get_logger
from app.integrations.crm.leadrat.endpoints.get_all_leads import (
    build_body,
    directory_for,
    extract_rows,
    to_lead,
    total_count,
)
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.lead import LeadFilters, LeadPage

log = get_logger(__name__)

PATH = "/lead/custom-filters"
DEFAULT_PAGE_SIZE = 10


def get_leads_custom_filters(
    http: LeadratHttp,
    filters: LeadFilters,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> LeadPage:
    body = build_body(filters, page, page_size)
    body["path"] = PATH.lstrip("/")
    payload = http.post(PATH, body)
    rows = extract_rows(payload)
    total = total_count(payload)
    log.info("get_leads_custom_filters -> %d rows (total %s)", len(rows), total)
    directory = directory_for(rows)
    return LeadPage(total=total, leads=[to_lead(row, directory) for row in rows])
