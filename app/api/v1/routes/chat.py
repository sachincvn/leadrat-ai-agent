from fastapi import APIRouter

from app.api.deps import CallerDep
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import clear_chat_history, handle_chat

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, caller: CallerDep) -> ChatResponse:
    return handle_chat(request, caller)


@router.delete("/history")
def clear_history(caller: CallerDep) -> dict:
    """Forget this caller's conversation so far - the next message starts fresh."""
    clear_chat_history(caller)
    return {"cleared": True}
