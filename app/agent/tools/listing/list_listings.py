"""Tool: list or search listings (properties published to a listing site).

Backed by POST /listingsite/all.
"""

import json

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client
from app.schemas.listing import Listing, ListingFilters

MAX_LISTINGS = 15
SAMPLE_FIELDS = ("id", "title", "status", "project", "no_of_bedroom", "no_of_bathroom", "lead_count")


def _compact(listing: Listing) -> dict:
    data = listing.model_dump()
    return {key: data[key] for key in SAMPLE_FIELDS if data.get(key) is not None}


@tool
def list_listings(keyword: str = "", location: str = "", limit: int = 10) -> str:
    """List or search the tenant's published listings (properties on a
    listing site/portal - distinct from the internal property records
    list_properties returns).

    Call with no arguments for "show all listings" or "how many listings do
    we have". The result reports the total number of matching listings and a
    sample of them.

    keyword  - a listing title to search for
    location - city

    Pass only values the user actually stated. Leave the rest empty.
    """
    filters = ListingFilters(
        keyword=keyword or None,
        location=location or None,
        limit=max(1, min(limit, MAX_LISTINGS)),
    )
    page = get_crm_client().search_listings(filters)

    return json.dumps(
        {
            "total_matching_listings": page.total,
            "showing": len(page.listings),
            "listings": [_compact(entry) for entry in page.listings],
        },
        default=str,
    )
