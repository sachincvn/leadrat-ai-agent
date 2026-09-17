"""Tool: list or search projects.

Backed by POST /project.
"""

import json

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client
from app.schemas.project import Project, ProjectFilters

MAX_PROJECTS = 15
SAMPLE_FIELDS = ("id", "name", "status", "current_status", "min_price", "max_price", "possession_date")


def _compact(project: Project) -> dict:
    data = project.model_dump()
    return {key: data[key] for key in SAMPLE_FIELDS if data.get(key) is not None}


@tool
def list_projects(keyword: str = "", location: str = "", limit: int = 10) -> str:
    """List or search the tenant's real estate projects.

    Call with no arguments for "show all projects" or "how many projects do
    we have". The result reports the total number of matching projects and a
    sample of them.

    keyword  - a project name to search for
    location - city

    Pass only values the user actually stated. Leave the rest empty.
    """
    filters = ProjectFilters(
        keyword=keyword or None,
        location=location or None,
        limit=max(1, min(limit, MAX_PROJECTS)),
    )
    page = get_crm_client().search_projects(filters)

    return json.dumps(
        {
            "total_matching_projects": page.total,
            "showing": len(page.projects),
            "projects": [_compact(p) for p in page.projects],
        },
        default=str,
    )
