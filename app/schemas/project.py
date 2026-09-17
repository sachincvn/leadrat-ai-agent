"""Project domain models, shaped after the Leadrat project-search response."""

from pydantic import BaseModel


class Project(BaseModel):
    id: str
    name: str | None = None
    status: str | None = None
    current_status: str | None = None
    total_flats: float | None = None
    total_blocks: float | None = None
    min_price: float | None = None
    max_price: float | None = None
    possession_date: str | None = None
    created_at: str | None = None


class ProjectPage(BaseModel):
    """One page of projects plus how many matched in total."""

    total: int | None = None
    projects: list[Project] = []


class ProjectFilters(BaseModel):
    """What the agent may filter on today.

    Maps onto the Leadrat request body in
    `integrations/crm/leadrat/endpoints/get_projects.py`.
    """

    keyword: str | None = None
    location: str | None = None
    min_price: int | None = None
    max_price: int | None = None
    limit: int = 10


class ProjectCounts(BaseModel):
    """Top-level project counts, from POST /project/count."""

    all: int | None = None
    residential: int | None = None
    commercial: int | None = None
    agriculture: int | None = None


class ProjectLeadCount(BaseModel):
    """One project's lead/prospect/visit counts, from POST /tempproject/leads-count."""

    project_id: str | None = None
    lead_count: int | None = None
    prospect_count: int | None = None
    meeting_done_count: int | None = None
    site_visit_done_count: int | None = None
