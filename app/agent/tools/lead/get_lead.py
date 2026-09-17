"""Tool: fetch one lead by id."""

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client


@tool
def get_lead(lead_id: str) -> str:
    """Get the details of one lead by its id, for example L001."""
    return get_crm_client().get_lead(lead_id).model_dump_json()
