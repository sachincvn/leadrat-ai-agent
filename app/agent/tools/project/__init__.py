"""Project tools, one file per API."""

from app.agent.tools.project.get_project_count import get_project_count
from app.agent.tools.project.get_project_leads_count import get_project_leads_count
from app.agent.tools.project.list_projects import list_projects

PROJECT_TOOLS = [list_projects, get_project_count, get_project_leads_count]
