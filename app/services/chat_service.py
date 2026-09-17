"""Use-case layer between the API and the agent.

Orchestration lives here - the caller's identity scope, and later conversation
memory, source collection and the write-confirmation flow.
"""

from app.agent import run_agent
from app.api.deps import Caller
from app.core.context import use_caller
from app.schemas.chat import ChatRequest, ChatResponse


def handle_chat(request: ChatRequest, caller: Caller) -> ChatResponse:
    # Every CRM call made by a tool inside this block runs as the caller.
    with use_caller(caller.jwt, caller.tenant):
        result = run_agent(message=request.message, lead_id=request.lead_id)
    return ChatResponse(answer=result.answer, tools_used=result.tools_used)
