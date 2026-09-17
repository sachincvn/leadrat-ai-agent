"""POST /tempproject/leads-count - lead/prospect/visit counts for specific projects.

Confirmed against the live Swagger spec (operation MCP_GetLeadsCount, request
body GetLeadsCountByProjectIdsRequest = {"ids": [...]}, checked 2026-09-17).
"""

from typing import Any

from app.core.logging import get_logger
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.project import ProjectLeadCount

log = get_logger(__name__)

PATH = "/tempproject/leads-count"


def build_body(project_ids: list[str]) -> dict:
    return {"ids": project_ids}


def to_count(row: dict) -> ProjectLeadCount:
    return ProjectLeadCount(
        project_id=str(row.get("projectId") or ""),
        lead_count=row.get("leadCount"),
        prospect_count=row.get("prospectCount"),
        meeting_done_count=row.get("meetingDoneCount"),
        site_visit_done_count=row.get("siteVisitDoneCount"),
    )


def get_project_leads_count(http: LeadratHttp, project_ids: list[str]) -> list[ProjectLeadCount]:
    payload = http.post(PATH, build_body(project_ids))
    rows: Any = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return []
    return [to_count(row) for row in rows if isinstance(row, dict)]
