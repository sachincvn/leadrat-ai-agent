"""Lead domain models, shaped after the Leadrat lead-search response."""

from pydantic import BaseModel


class Lead(BaseModel):
    id: str
    name: str
    phone: str | None = None
    email: str | None = None
    source: str | None = None
    sub_source: str | None = None
    status: str | None = None
    location: str | None = None
    project: str | None = None
    requirement: str | None = None
    assigned_to: str | None = None
    lead_number: str | None = None
    scheduled_at: str | None = None
    created_at: str | None = None
    last_modified_at: str | None = None


class LeadPage(BaseModel):
    """One page of leads plus how many matched in total."""

    total: int | None = None
    leads: list[Lead] = []


class LeadFilters(BaseModel):
    """What the agent may filter on today.

    Maps onto the Leadrat request body in
    `integrations/crm/leadrat/endpoints/get_all_leads.py`.
    """

    keyword: str | None = None
    location: str | None = None
    source: str | None = None
    status: str | None = None
    lead_ids: list[str] | None = None
    status_ids: list[str] | None = None
    assigned_to_ids: list[str] | None = None
    limit: int = 10


class LeadStatusCount(BaseModel):
    """One status's (or sub-status's) lead count, from the custom-filters-count API."""

    name: str | None = None
    count: int = 0
    sub_status_counts: list["LeadStatusCount"] | None = None


class LeadBaseFilterCounts(BaseModel):
    """Generic base-filter lead counts, from POST /lead/new/counts/basefilter."""

    all_leads_count: int = 0
    my_leads_count: int = 0
    team_leads_count: int = 0
    unassign_leads_count: int | None = None
    deleted_leads_count: int = 0
    duplicate_leads_count: int = 0
    re_enquired_leads_count: int = 0
    pending_assignment_leads_count: int = 0
