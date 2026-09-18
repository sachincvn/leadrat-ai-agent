"""Use-case layer between the API and the agent.

Orchestration lives here - the caller's identity scope, conversation memory,
and later source collection and the write-confirmation flow.
"""

from collections.abc import Iterator

from app.agent.runner import run_agent, stream_agent
from app.api.deps import Caller
from app.core.context import iter_as_caller, use_caller
from app.core.jwt_claims import user_id as jwt_user_id
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import chat_history_store


def _session_key(caller: Caller, conversation_id: str | None = None) -> str:
    """Which conversation a turn belongs to.

    The identity half comes from the caller's own JWT rather than anything the
    client sends, so one user can never read another's history by guessing an
    id. The conversation half is the client's, which is what lets a user keep
    several threads and come back to one - a client that sends nothing keeps
    the single running conversation it always had.
    """
    uid = jwt_user_id(caller.jwt) or caller.jwt
    session = f"{caller.tenant}:{uid}"
    return f"{session}:{conversation_id}" if conversation_id else session


def handle_chat(request: ChatRequest, caller: Caller) -> ChatResponse:
    session_key = _session_key(caller, request.conversation_id)
    history = chat_history_store.get_history(session_key)
    recent_tool_notes = chat_history_store.get_tool_notes(session_key)

    # Every CRM call made by a tool inside this block runs as the caller.
    with use_caller(caller.jwt, caller.tenant):
        result = run_agent(
            message=request.message,
            lead_id=request.lead_id,
            history=history,
            recent_tool_notes=recent_tool_notes,
        )

    chat_history_store.append_turn(
        session_key, request.message, result.answer, result.tool_notes
    )
    return ChatResponse(answer=result.answer, tools_used=result.tools_used)


def stream_chat(request: ChatRequest, caller: Caller) -> Iterator[dict]:
    """The same turn as handle_chat, yielded piece by piece.

    History is written once the turn finishes, exactly as in handle_chat - a
    stream the client abandons half way leaves no half-answer in memory.
    """
    session_key = _session_key(caller, request.conversation_id)
    history = chat_history_store.get_history(session_key)
    recent_tool_notes = chat_history_store.get_tool_notes(session_key)

    events = iter_as_caller(
        caller.jwt,
        caller.tenant,
        lambda: stream_agent(
            message=request.message,
            lead_id=request.lead_id,
            history=history,
            recent_tool_notes=recent_tool_notes,
            renders_blocks=request.renders_blocks,
        ),
    )
    for event in events:
        if event.kind == "done":
            chat_history_store.append_turn(
                session_key,
                request.message,
                event.data["answer"],
                event.data["tool_notes"],
            )
            yield {"type": "done", "tools_used": event.data["tools_used"]}
        else:
            yield {"type": event.kind, **event.data}


def clear_chat_history(caller: Caller, conversation_id: str | None = None) -> None:
    chat_history_store.clear(_session_key(caller, conversation_id))
