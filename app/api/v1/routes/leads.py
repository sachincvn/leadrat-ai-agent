from fastapi import APIRouter, Query

from app.api.deps import CallerDep
from app.core.context import use_caller
from app.integrations.crm.factory import get_crm_client
from app.schemas.lead import Lead, LeadFilters, LeadPage
from app.schemas.lead_chat import LeadChatRequest, LeadChatResponse
from app.services.lead_chat_service import handle_lead_chat

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("/search", response_model=LeadPage)
def search_leads(
    caller: CallerDep,
    keyword: str | None = None,
    location: str | None = None,
    source: str | None = None,
    status: str | None = None,
    limit: int = Query(10, ge=1, le=500),
) -> LeadPage:
    with use_caller(caller.jwt, caller.tenant):
        filters = LeadFilters(
            keyword=keyword,
            location=location,
            source=source,
            status=status,
            limit=limit,
        )
        return get_crm_client().search_leads(filters)


@router.get("/{lead_id}", response_model=Lead)
def get_lead(lead_id: str, caller: CallerDep) -> Lead:
    with use_caller(caller.jwt, caller.tenant):
        return get_crm_client().get_lead(lead_id)


@router.post("/{lead_id}/chat", response_model=LeadChatResponse)
def lead_chat(lead_id: str, request: LeadChatRequest, caller: CallerDep) -> LeadChatResponse:
    """Ask a question about one lead using its history.

    Stateless: nothing about the message, the history looked up, or the
    answer is stored - each call is answered from scratch, with no
    conversation id and no server-side memory.
    """
    return handle_lead_chat(lead_id, request, caller)
