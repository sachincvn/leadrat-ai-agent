"""Listing domain models, shaped after the Leadrat listing-search response.

A "listing" is a property published to a listing site/portal - distinct from
a plain property record (see `app/schemas/property.py`).
"""

from pydantic import BaseModel


class Listing(BaseModel):
    id: str
    title: str | None = None
    status: str | None = None
    project: str | None = None
    no_of_bedroom: float | None = None
    no_of_bathroom: float | None = None
    unit_number: str | None = None
    lead_count: int | None = None
    created_at: str | None = None


class ListingPage(BaseModel):
    """One page of listings plus how many matched in total."""

    total: int | None = None
    listings: list[Listing] = []


class ListingFilters(BaseModel):
    """What the agent may filter on today.

    Maps onto the Leadrat request body in
    `integrations/crm/leadrat/endpoints/get_listings.py`.
    """

    keyword: str | None = None
    location: str | None = None
    min_price: int | None = None
    max_price: int | None = None
    limit: int = 10


class ListingTopCounts(BaseModel):
    """Listing status counts, from POST /listingsite/listing/top-count."""

    all: int | None = None
    draft: int | None = None
    approved: int | None = None
    refused: int | None = None
    archived: int | None = None
    sold: int | None = None
    pending_approval: int | None = None
    taken_down: int | None = None
    expired: int | None = None
    pocket_listing: int | None = None


class ListingBaseCounts(BaseModel):
    """Listing category counts, from POST /listingsite/listing/base-count."""

    all: int | None = None
    residential: int | None = None
    commercial: int | None = None
