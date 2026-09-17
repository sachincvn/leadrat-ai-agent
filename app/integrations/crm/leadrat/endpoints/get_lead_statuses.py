"""GET /status - the full lead-status tree (parents + nested sub-statuses).

Used internally to resolve status ids to readable names for
get_lead_status_counts, whose /lead/counts/statuses response carries ids only.
"""

from app.integrations.crm.leadrat.http import LeadratHttp

PATH = "/status"
PAGE_SIZE = 500


def get_lead_status_tree(http: LeadratHttp) -> list[dict]:
    payload = http.get(PATH, params={"pageNumber": 1, "pageSize": PAGE_SIZE})
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload["items"]
    return []


def status_name_map(http: LeadratHttp) -> dict[str, str]:
    """Flat status id -> display name, over parents and nested sub-statuses."""
    name_by_id: dict[str, str] = {}

    def add(node: dict) -> None:
        status_id = node.get("id")
        if status_id:
            name_by_id[str(status_id)] = node.get("displayName") or node.get("actionName") or node.get("status")
        for child in node.get("childTypes") or []:
            add(child)

    for status in get_lead_status_tree(http):
        add(status)
    return name_by_id
