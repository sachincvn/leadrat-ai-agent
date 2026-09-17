"""In-memory conversation history, keyed by session (tenant + user).

Process-local: fine for a single backend instance / a prototype like this
one. Swap the dict for Redis or a DB table if this needs to survive
restarts, or run across more than one backend process.
"""

from threading import Lock

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

# Messages kept per session (user + assistant turns combined) - a soft cap so
# a long-running conversation doesn't grow the prompt sent to the LLM without
# bound. 20 messages = the last 10 exchanges.
MAX_MESSAGES = 20

# Tool results carried forward, as whole turns. Two is enough for "and the
# second one?" while keeping the prompt small.
MAX_NOTE_TURNS = 2

_store: dict[str, list[BaseMessage]] = {}
_notes: dict[str, list[list[str]]] = {}
_lock = Lock()


def get_history(session_key: str) -> list[BaseMessage]:
    with _lock:
        return list(_store.get(session_key, []))


def get_tool_notes(session_key: str) -> list[str]:
    """Tool output from the last few turns, flattened - context for follow-ups."""
    with _lock:
        return [note for turn in _notes.get(session_key, []) for note in turn]


def append_turn(
    session_key: str,
    user_message: str,
    answer: str,
    tool_notes: list[str] | None = None,
) -> None:
    with _lock:
        if tool_notes:
            turns = _notes.setdefault(session_key, [])
            turns.append(tool_notes)
            del turns[:-MAX_NOTE_TURNS]
        history = _store.setdefault(session_key, [])
        history.append(HumanMessage(user_message))
        history.append(AIMessage(answer))
        if len(history) > MAX_MESSAGES:
            del history[: len(history) - MAX_MESSAGES]


def clear(session_key: str) -> None:
    with _lock:
        _store.pop(session_key, None)
        _notes.pop(session_key, None)
