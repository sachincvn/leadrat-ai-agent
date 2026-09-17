"""GET /customamenityandattribute/get/all/categories/with/amenities.

Confirmed against the live Swagger spec (checked 2026-09-17). No request
body, no query params, requires the tenant header like most endpoints.

Response uses the standard envelope (not the items/itemsCount one the
masterdata/status endpoints use): {"succeeded", "message", "errors",
"data": [{"categoryName", "amenities": [...]}], ...}. Each amenity carries
~12 raw fields (image URLs, per-property-type visibility, audit fields,
...) - to_amenity() keeps only what's useful for the agent.
"""

from typing import Any

from app.core.logging import get_logger
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.masterdata import Amenity, AmenityCategory

log = get_logger(__name__)

PATH = "/customamenityandattribute/get/all/categories/with/amenities"


def extract_rows(payload: Any) -> list[dict]:
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]

    log.warning(
        "Unrecognised amenity-categories response envelope. Top-level keys: %s",
        list(payload) if isinstance(payload, dict) else type(payload).__name__,
    )
    return []


def to_amenity(row: dict) -> Amenity:
    return Amenity(
        id=row.get("masterAmenityId"),
        name=row.get("amenityName"),
        display_name=row.get("amenityDisplayName"),
        type=row.get("amenityType"),
        is_active=row.get("isActive"),
        order_rank=row.get("orderRank"),
    )


def to_category(row: dict) -> AmenityCategory:
    amenities = row.get("amenities") or []
    return AmenityCategory(
        category_name=row.get("categoryName"),
        amenities=[to_amenity(a) for a in amenities if isinstance(a, dict)],
    )


def get_amenity_categories(http: LeadratHttp) -> list[AmenityCategory]:
    payload = http.get(PATH)
    rows = extract_rows(payload)
    log.info("get_amenity_categories -> %d categories", len(rows))
    return [to_category(row) for row in rows]
