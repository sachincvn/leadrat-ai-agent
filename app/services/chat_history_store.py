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

_store: dict[str, list[BaseMessage]] = {}
_lock = Lock()


def get_history(session_key: str) -> list[BaseMessage]:
    with _lock:
        return list(_store.get(session_key, []))


def append_turn(session_key: str, user_message: str, answer: str) -> None:
    with _lock:
        history = _store.setdefault(session_key, [])
        history.append(HumanMessage(user_message))
        history.append(AIMessage(answer))
        if len(history) > MAX_MESSAGES:
            del history[: len(history) - MAX_MESSAGES]


def clear(session_key: str) -> None:
    with _lock:
        _store.pop(session_key, None)
