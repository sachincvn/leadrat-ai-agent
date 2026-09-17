"""POST /project/count - top-level project counts by category.

Confirmed against the live Swagger spec (operation "Get Project Top Level
Count", request body GetProjectTopLevelCountRequest -> the same
GetAllProjectParameter filter shape as project search, checked 2026-09-17).
"""

from typing import Any

from app.core.logging import get_logger
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.project import ProjectCounts, ProjectFilters

log = get_logger(__name__)

PATH = "/project/count"


def build_body(filters: ProjectFilters | None = None) -> dict:
    body: dict[str, Any] = {"pageNumber": 1, "pageSize": 1, "orderBy": []}
    if filters and filters.location:
        body["locations"] = [filters.location]
    return body


def get_project_count(http: LeadratHttp, filters: ProjectFilters | None = None) -> ProjectCounts | None:
    payload = http.post(PATH, build_body(filters))
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return None

    return ProjectCounts(
        all=data.get("all"),
        residential=data.get("residential"),
        commercial=data.get("commercial"),
        agriculture=data.get("agriculture"),
    )
