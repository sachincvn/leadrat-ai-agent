"""Property domain models, shaped after the Leadrat property-search response."""

from pydantic import BaseModel


class Property(BaseModel):
    id: str
    title: str | None = None
    status: str | None = None
    sale_type: str | None = None
    furnish_status: str | None = None
    no_of_bhk: float | None = None
    project: str | None = None
    unit_no: int | None = None
    created_at: str | None = None


class PropertyPage(BaseModel):
    """One page of properties plus how many matched in total."""

    total: int | None = None
    properties: list[Property] = []


class PropertyFilters(BaseModel):
    """What the agent may filter on today.

    Maps onto the Leadrat request body in
    `integrations/crm/leadrat/endpoints/get_properties.py`.
    """

    keyword: str | None = None
    location: str | None = None
    property_type: str | None = None
    min_price: int | None = None
    max_price: int | None = None
    limit: int = 10


class PropertyCounts(BaseModel):
    """Top-level property counts, from POST /property/count."""

    all: int | None = None
    residential: int | None = None
    commercial: int | None = None
    agricultural: int | None = None
