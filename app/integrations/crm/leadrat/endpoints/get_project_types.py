"""GET /masterdata/masterprojecttypes - the tenant's project-type hierarchy.

Confirmed against the live Swagger spec (operation under
`/api/v1/mcp/masterdata/masterprojecttypes`, GET, checked 2026-09-17).
Same shape as get_property_types.py: no body/query params, no tenant header
in the spec (looks like global master data), Bearer-secured, and a
recursive `childTypes` tree. See that module's docstring for the envelope
details - this is the same {"items": [...], "itemsCount", "totalCount"} shape.
"""

from typing import Any

from app.core.logging import get_logger
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.masterdata import ProjectType

log = get_logger(__name__)

PATH = "/masterdata/masterprojecttypes"


def extract_items(payload: Any) -> list[dict]:
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload["items"]

    log.warning(
        "Unrecognised project-types response envelope. Top-level keys: %s",
        list(payload) if isinstance(payload, dict) else type(payload).__name__,
    )
    return []


def to_project_type(row: dict) -> ProjectType:
    children = row.get("childTypes") or []
    return ProjectType(
        id=str(row.get("id") or ""),
        type=row.get("type"),
        display_name=row.get("displayName"),
        level=row.get("level"),
        children=[to_project_type(c) for c in children if isinstance(c, dict)],
    )


def get_project_types(http: LeadratHttp) -> list[ProjectType]:
    payload = http.get(PATH)
    rows = extract_items(payload)
    log.info("get_project_types -> %d top-level rows", len(rows))
    return [to_project_type(row) for row in rows]
