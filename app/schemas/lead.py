"""Lead domain models."""

from pydantic import BaseModel


class Lead(BaseModel):
    id: str
    name: str
    phone: str | None = None
    email: str | None = None
    source: str | None = None
    status: str | None = None
    sub_status: str | None = None
    location: str | None = None
    project: str | None = None
    budget: float | None = None
    requirement: str | None = None
    assigned_to: str | None = None
    last_contacted_at: str | None = None
    recent_activity: list[str] = []


class LeadFilters(BaseModel):
    """What the agent may filter on today.

    Deliberately small: it maps onto the Leadrat request body in
    `integrations/crm/leadrat/endpoints/get_all_leads.py`. Grow it as the
    lookup endpoints for enum ids (source, budget, bhk) get wired.
    """

    keyword: str | None = None
    location: str | None = None
    source: str | None = None
    status: str | None = None
    lead_ids: list[str] | None = None
    status_ids: list[str] | None = None
    assigned_to_ids: list[str] | None = None
    limit: int = 20
