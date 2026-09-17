from fastapi import APIRouter

from app.api.deps import CallerDep
from app.schemas.assistant import AssistantTurnRequest, AssistantTurnResponse
from app.services.assistant_service import handle_turn

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/turn", response_model=AssistantTurnResponse)
def turn(request: AssistantTurnRequest, caller: CallerDep) -> AssistantTurnResponse:
    """One assistant turn.

    Send `message` for a new user message, or `tool_results` to report back on
    the plan from the previous turn. Declare `capabilities: ["ui_actions"]` if
    this client can execute UI steps.
    """
    return handle_turn(request, caller)
