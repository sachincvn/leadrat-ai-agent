"""Tool: a lead's field-change audit trail - assignment, notes, status changes.

Backed by GET /lead/histories/{id}, confirmed against the live Swagger spec
(see the endpoint module docstring in
integrations/crm/leadrat/endpoints/get_lead_history.py).
"""

import json

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client

MAX_ENTRIES = 15


@tool
def get_lead_history(lead_id: str, limit: int = 10) -> str:
    """Get a lead's change history: assignment, notes, and status changes.

    Use this for "what happened with this lead", "when did the status
    change", "who was this assigned to before" - anything about how a lead's
    record has changed over time. This is a field-change audit trail, not a
    call/meeting log. Use get_lead instead for the lead's current details,
    and search_leads to find leads rather than look at one lead's history.

    lead_id - the lead's id, e.g. L001
    limit   - how many recent entries to show, 1 to 15
    """
    page = get_crm_client().get_lead_history(lead_id, limit=max(1, min(limit, MAX_ENTRIES)))

    return json.dumps(
        {
            "total_entries": page.total,
            "showing": len(page.entries),
            "history": [entry.model_dump(exclude_none=True) for entry in page.entries],
        },
        default=str,
    )
