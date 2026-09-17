"""Master/reference-data models, shaped after the Leadrat masterdata responses.

These back a set of "what are the valid values for X" lookups: property
types, project types, area units, lead statuses, and amenity categories.
Unlike leads/users, most of these come back as a shallow type hierarchy
(a type can have child types), so the models are self-referential.
"""

from pydantic import BaseModel


class PropertyType(BaseModel):
    """One row from GET /masterdata/propertytypes."""

    id: str
    type: str | None = None
    display_name: str | None = None
    level: int | None = None
    children: list["PropertyType"] = []


class ProjectType(BaseModel):
    """One row from GET /masterdata/masterprojecttypes."""

    id: str
    type: str | None = None
    display_name: str | None = None
    level: int | None = None
    children: list["ProjectType"] = []


class AreaUnit(BaseModel):
    """One row from GET /masterdata/masterareaunits."""

    unit: str | None = None
    conversion_factor: float | None = None
    order_rank: int | None = None


class LeadStatus(BaseModel):
    """One row from GET /status - a tenant's configured lead-status tree."""

    id: str
    status: str | None = None
    display_name: str | None = None
    order_rank: int | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    color: str | None = None
    children: list["LeadStatus"] = []


class Amenity(BaseModel):
    """One amenity within an AmenityCategory."""

    id: str | None = None
    name: str | None = None
    display_name: str | None = None
    type: str | None = None
    is_active: bool | None = None
    order_rank: int | None = None


class AmenityCategory(BaseModel):
    """One row from GET /customamenityandattribute/get/all/categories/with/amenities."""

    category_name: str | None = None
    amenities: list[Amenity] = []
