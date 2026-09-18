"""In-memory conversation history, keyed by session (tenant + user + thread).

Process-local: fine for a single backend instance / a prototype like this
one. Swap the dict for Redis or a DB table if this needs to survive
restarts, or run across more than one backend process.
"""

from collections import OrderedDict
from threading import Lock

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

# Messages kept per session (user + assistant turns combined) - a soft cap so
# a long-running conversation doesn't grow the prompt sent to the LLM without
# bound. 20 messages = the last 10 exchanges.
MAX_MESSAGES = 20

# Tool results carried forward, as whole turns. Two is enough for "and the
# second one?" while keeping the prompt small.
MAX_NOTE_TURNS = 2

# Sessions held at once, across every user. Each client keeps several named
# conversations, so without a bound this dict would grow for as long as the
# process lives. The least recently written one goes first; a client that
# comes back to an evicted conversation still has its own transcript, and the
# model simply starts that thread fresh.
MAX_SESSIONS = 500

_store: OrderedDict[str, list[BaseMessage]] = OrderedDict()
_notes: dict[str, list[list[str]]] = {}
_lock = Lock()


def _evict_oldest() -> None:
    while len(_store) > MAX_SESSIONS:
        oldest, _ = _store.popitem(last=False)
        _notes.pop(oldest, None)


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
        _store.move_to_end(session_key)
        _evict_oldest()


def clear(session_key: str) -> None:
    with _lock:
        _store.pop(session_key, None)
        _notes.pop(session_key, None)
