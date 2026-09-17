"""Tool: listing counts by category (residential vs commercial).

Backed by POST /listingsite/listing/base-count.
"""

import json

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client


@tool
def get_listing_base_count() -> str:
    """Get listing counts broken down by category - residential vs commercial.

    Use this for "how many residential listings", "how many commercial
    listings" - counts only, not the listing list itself (use list_listings
    for that).
    """
    counts = get_crm_client().get_listing_base_count()
    if counts is None:
        return json.dumps({"error": "No count data returned"})
    return counts.model_dump_json(exclude_none=True)
