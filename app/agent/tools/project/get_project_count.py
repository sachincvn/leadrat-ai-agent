"""Tool: top-level project counts by category.

Backed by POST /project/count.
"""

import json

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client


@tool
def get_project_count() -> str:
    """Get the total number of projects, broken down by category (residential,
    commercial, agriculture).

    Use this for "how many projects total", "how many commercial projects" -
    counts only, not the project list itself (use list_projects for that).
    """
    counts = get_crm_client().get_project_count()
    if counts is None:
        return json.dumps({"error": "No count data returned"})
    return counts.model_dump_json(exclude_none=True)
