"""Lead domain models."""

from pydantic import BaseModel


class Lead(BaseModel):
    id: str
    name: str
    source: str | None = None
    status: str | None = None
    location: str | None = None
    project: str | None = None
    budget: float | None = None
    requirement: str | None = None
    assigned_to: str | None = None
    last_contacted_at: str | None = None
    recent_activity: list[str] = []


class LeadFilters(BaseModel):
    source: str | None = None
    status: str | None = None
    location: str | None = None
