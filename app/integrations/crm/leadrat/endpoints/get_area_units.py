"""GET /masterdata/masterareaunits - the tenant's area-unit list (sq.ft, acre, ...).

Confirmed against the live Swagger spec (operation under
`/api/v1/mcp/masterdata/masterareaunits`, GET, checked 2026-09-17). No body,
no query params, no tenant header in the spec (global master data like
property/project types), Bearer-secured. Same {"items": [...], "itemsCount",
"totalCount"} envelope. Flat list, no nesting.
"""

from typing import Any

from app.core.logging import get_logger
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.masterdata import AreaUnit

log = get_logger(__name__)

PATH = "/masterdata/masterareaunits"


def extract_items(payload: Any) -> list[dict]:
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload["items"]

    log.warning(
        "Unrecognised area-units response envelope. Top-level keys: %s",
        list(payload) if isinstance(payload, dict) else type(payload).__name__,
    )
    return []


def to_area_unit(row: dict) -> AreaUnit:
    return AreaUnit(
        unit=row.get("unit"),
        conversion_factor=row.get("conversionFactor"),
        order_rank=row.get("orderRank"),
    )


def get_area_units(http: LeadratHttp) -> list[AreaUnit]:
    payload = http.get(PATH)
    rows = extract_items(payload)
    log.info("get_area_units -> %d rows", len(rows))
    return [to_area_unit(row) for row in rows]
