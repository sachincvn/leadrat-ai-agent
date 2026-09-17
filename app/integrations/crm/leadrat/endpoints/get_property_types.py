"""GET /masterdata/propertytypes - the tenant's property-type hierarchy.

Confirmed against the live Swagger spec at
https://connect.leadrat.info/swagger/v1/swagger.json (operation under
`/api/v1/mcp/masterdata/propertytypes`, GET, checked 2026-09-17).

No request body, no query params, and notably no `tenant` header in the
spec either - unlike every other endpoint touched so far, this one (and
masterprojecttypes/masterareaunits alongside it) looks to be global master
data shared across tenants rather than tenant-scoped. Still Bearer-secured.
LeadratHttp sends the tenant header on every call regardless - Leadrat
appears to just ignore the extra header on endpoints that don't need it.

Response envelope is the generic paged shape: {"succeeded", "message",
"errors", "data" (unused here), "items": [MasterPropertyTypeDto], "itemsCount",
"totalCount", ...} - rows live under "items", not "data". Each row can carry
nested `childTypes` (e.g. "Residential" -> "Apartment"/"Villa"), mapped
recursively below.
"""

from typing import Any

from app.core.logging import get_logger
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.masterdata import PropertyType

log = get_logger(__name__)

PATH = "/masterdata/propertytypes"


def extract_items(payload: Any) -> list[dict]:
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload["items"]

    log.warning(
        "Unrecognised property-types response envelope. Top-level keys: %s",
        list(payload) if isinstance(payload, dict) else type(payload).__name__,
    )
    return []


def to_property_type(row: dict) -> PropertyType:
    children = row.get("childTypes") or []
    return PropertyType(
        id=str(row.get("id") or ""),
        type=row.get("type"),
        display_name=row.get("displayName"),
        level=row.get("level"),
        children=[to_property_type(c) for c in children if isinstance(c, dict)],
    )


def get_property_types(http: LeadratHttp) -> list[PropertyType]:
    payload = http.get(PATH)
    rows = extract_items(payload)
    log.info("get_property_types -> %d top-level rows", len(rows))
    return [to_property_type(row) for row in rows]
