"""POST /property/count - top-level property counts by category.

Confirmed against the live Swagger spec (operation MCP_Search4, request body
V2GetAllPropertyCountRequest -> the same GetAllPropertyParameters filter
shape as property search, checked 2026-09-17).
"""

from typing import Any

from app.core.logging import get_logger
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.property import PropertyCounts, PropertyFilters

log = get_logger(__name__)

PATH = "/property/count"


def build_body(filters: PropertyFilters | None = None) -> dict:
    body: dict[str, Any] = {"pageNumber": 1, "pageSize": 1, "orderBy": []}
    if filters and filters.location:
        body["cities"] = [filters.location]
    return body


def get_property_count(http: LeadratHttp, filters: PropertyFilters | None = None) -> PropertyCounts | None:
    payload = http.post(PATH, build_body(filters))
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return None

    return PropertyCounts(
        all=data.get("allPropertiesCount"),
        residential=data.get("residentialPropertiesCount"),
        commercial=data.get("commercialPropertiesCount"),
        agricultural=data.get("agriculturalPropertiesCount"),
    )
