"""Tool: lead/prospect/site-visit counts for specific projects.

Backed by POST /tempproject/leads-count.
"""

import json

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client


@tool
def get_project_leads_count(project_ids: list[str]) -> str:
    """Get lead, prospect, and site-visit counts for one or more specific
    projects.

    project_ids - the projects' ids (guids). Don't have them? Call
    list_projects first to find them by name - never guess or invent an id.

    Use this for "how many leads does project X have", "which project has
    the most site visits" once you know the project id(s).
    """
    counts = get_crm_client().get_project_leads_count(project_ids)
    return json.dumps([c.model_dump(exclude_none=True) for c in counts], default=str)
