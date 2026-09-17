"""Use-case layer for the capability-aware assistant.

Mirrors chat_service: scope the caller's identity, run the agent, return the
contract object. The read-only chat path is untouched.
"""

from app.agent.guided import run_turn
from app.api.deps import Caller
from app.core.context import use_caller
from app.schemas.assistant import AssistantTurnRequest, AssistantTurnResponse


def handle_turn(request: AssistantTurnRequest, caller: Caller) -> AssistantTurnResponse:
    # Every CRM call made by a tool inside this block runs as the caller.
    with use_caller(caller.jwt, caller.tenant):
        return run_turn(request)
