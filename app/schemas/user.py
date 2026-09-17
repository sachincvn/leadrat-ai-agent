"""User domain models, shaped after the Leadrat user-profile responses."""

from pydantic import BaseModel


class UserSummary(BaseModel):
    """One row from GET /user/getalluserswithroles - enough to resolve a
    name to an id before calling get_user_profile."""

    id: str
    user_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool | None = None
    roles: list[str] = []


class UserProfile(BaseModel):
    """A trimmed view of GET /userprofile/{id}.

    The raw response carries ~50 fields (documents, role permissions,
    general settings, time zone, mcpConnect flags, ...) - only what's useful
    on the agent/chat surface is kept here. See the module docstring in
    `integrations/crm/leadrat/endpoints/get_user_profile.py`.
    """

    user_id: str
    user_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone_number: str | None = None
    is_active: bool | None = None
    designation: str | None = None
    department: str | None = None
    reports_to: str | None = None
    office_name: str | None = None
    lead_count: int | None = None
    roles: list[str] = []
