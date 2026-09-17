"""Tool: listing counts by status (draft, approved, sold, expired, ...).

Backed by POST /listingsite/listing/top-count.
"""

import json

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client


@tool
def get_listing_top_count() -> str:
    """Get listing counts broken down by status - draft, approved, refused,
    archived, sold, pending approval, taken down, expired, pocket listing.

    Use this for "how many listings are sold", "how many are still in
    draft" - counts only, not the listing list itself (use list_listings for
    that).
    """
    counts = get_crm_client().get_listing_top_count()
    if counts is None:
        return json.dumps({"error": "No count data returned"})
    return counts.model_dump_json(exclude_none=True)
