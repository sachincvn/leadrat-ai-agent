"""POST /project - search projects with available filters.

Confirmed against the live Swagger spec (operation MCP_Search2, request body
GetAllProjectRequest -> GetAllProjectParameter, checked 2026-09-17).

pageNumber, pageSize and orderBy are required by the schema (not nullable).
Everything else is optional and, following the lead-search endpoint's lead,
omitted entirely when the user did not state it - not sent as "" or null.
"""

from typing import Any

from app.core.logging import get_logger
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.project import Project, ProjectFilters, ProjectPage

log = get_logger(__name__)

PATH = "/project"

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 200


def build_body(filters: ProjectFilters, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE) -> dict:
    body: dict[str, Any] = {
        "pageNumber": max(page, 1),
        "pageSize": min(page_size if page_size > 0 else DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE),
        "orderBy": [],
    }

    if filters.keyword:
        body["keyword"] = filters.keyword
    if filters.location:
        body["locations"] = [filters.location]
    if filters.min_price is not None:
        body["minPrice"] = filters.min_price
    if filters.max_price is not None:
        body["maxPrice"] = filters.max_price

    return body


def extract_rows(payload: Any) -> list[dict]:
    """Same envelope shape as the lead-search endpoint: {"items": [...], "totalCount": n}."""
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("items"), list):
        return payload["items"]
    log.warning("Unrecognised project response envelope. Top-level keys: %s", list(payload))
    return []


def total_count(payload: Any) -> int | None:
    if isinstance(payload, dict):
        count = payload.get("totalCount")
        if isinstance(count, int):
            return count
    return None


def _named(value: Any) -> str | None:
    """Leadrat's enum-like fields come back as {"displayName": ..., ...} or a bare string."""
    if isinstance(value, dict):
        return value.get("displayName") or value.get("name")
    return value


def to_project(row: dict) -> Project:
    return Project(
        id=str(row.get("id") or ""),
        name=row.get("name") or "Unknown",
        status=_named(row.get("status")),
        current_status=_named(row.get("currentStatus")),
        total_flats=row.get("totalFlats"),
        total_blocks=row.get("totalBlocks"),
        min_price=row.get("minimumPrice"),
        max_price=row.get("maximumPrice"),
        possession_date=row.get("possessionDate"),
        created_at=row.get("createdOn"),
    )


def get_projects(
    http: LeadratHttp,
    filters: ProjectFilters,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> ProjectPage:
    payload = http.post(PATH, build_body(filters, page, page_size))
    rows = extract_rows(payload)
    total = total_count(payload)
    log.info("get_projects -> %d rows (total %s)", len(rows), total)
    return ProjectPage(total=total, projects=[to_project(row) for row in rows])
