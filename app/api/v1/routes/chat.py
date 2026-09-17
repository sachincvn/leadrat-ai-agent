from fastapi import APIRouter

from app.api.deps import CallerDep
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import handle_chat

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, caller: CallerDep) -> ChatResponse:
    return handle_chat(request, caller)
