import json
from collections.abc import Iterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import CallerDep
from app.core.exceptions import MusoError
from app.core.logging import get_logger
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import clear_chat_history, handle_chat, stream_chat

log = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, caller: CallerDep) -> ChatResponse:
    return handle_chat(request, caller)


def _sse(events: Iterator[dict]) -> Iterator[str]:
    """Server-sent events, one JSON object per event.

    The status code is already sent by the time the first event is produced,
    so a failure part-way through cannot become an HTTP error - it is sent as
    a final `error` event for the client to render in place of the answer.
    """
    try:
        for event in events:
            yield f"data: {json.dumps(event)}\n\n"
    except MusoError as exc:
        yield f"data: {json.dumps({'type': 'error', 'message': exc.message})}\n\n"
    except Exception:  # noqa: BLE001 - never leak an internal failure into the stream
        log.exception("chat stream failed")
        yield f"data: {json.dumps({'type': 'error', 'message': 'MUSO is temporarily unavailable. Please try again in a moment.'})}\n\n"


@router.post("/stream")
def chat_stream(request: ChatRequest, caller: CallerDep) -> StreamingResponse:
    """The same answer as POST /chat, streamed as it is written.

    Events: `status` (a tool is running), `block` (a renderable block built
    from a tool result), `text` (append to the answer), `done` (with
    tools_used), `error`.
    """
    return StreamingResponse(
        _sse(stream_chat(request, caller)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.delete("/history")
def clear_history(caller: CallerDep, conversation_id: str | None = None) -> dict:
    """Forget one of this caller's conversations, or the unnamed one."""
    clear_chat_history(caller, conversation_id)
    return {"cleared": True}
