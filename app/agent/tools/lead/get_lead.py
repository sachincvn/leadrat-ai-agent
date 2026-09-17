"""Tool: fetch one lead by id."""

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client


@tool
def get_lead(lead_id: str) -> str:
    """Get the full details of ONE lead by its real id (a UUID such as
    3fa85f64-5717-4562-b3fc-2c963f66afa6 - never a made-up code).

    If you only have the lead's name or phone number, call search_leads with
    that first and use the id from its result - never guess or invent one
    here.
    """
    return get_crm_client().get_lead(lead_id).model_dump_json()
