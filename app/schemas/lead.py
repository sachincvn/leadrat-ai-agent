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


class LeadHistoryEntry(BaseModel):
    """One field-change audit entry on a lead, from Leadrat's
    GET /lead/histories/{id} (confirmed against the live Swagger spec -
    see `integrations/crm/leadrat/endpoints/get_lead_history.py`).
    """

    field_name: str | None = None  # which field changed, e.g. "Status"
    category: str | None = None  # filterKey: None, Assignment, Notes, Status
    old_value: str | None = None
    new_value: str | None = None
    updated_by: str | None = None
    updated_at: str | None = None
    action_type: str | None = None  # e.g. Create, Update


class LeadHistoryPage(BaseModel):
    """One page of a lead's history plus how many entries exist in total.

    Leadrat doesn't page this endpoint server-side - `total` is the full
    count and paging is applied client-side in get_lead_history.py.
    """

    total: int | None = None
    entries: list[LeadHistoryEntry] = []


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
