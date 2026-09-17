"""Use-case layer between the API and the agent.

Orchestration lives here — the caller's JWT scope, and later conversation
memory, source collection and the write-confirmation flow.
"""

from app.agent import run_agent
from app.core.context import use_jwt
from app.schemas.chat import ChatRequest, ChatResponse


def handle_chat(request: ChatRequest, jwt: str) -> ChatResponse:
    # Every CRM call made by a tool inside this block uses the caller's JWT.
    with use_jwt(jwt):
        result = run_agent(message=request.message, lead_id=request.lead_id)
    return ChatResponse(answer=result.answer, tools_used=result.tools_used)
