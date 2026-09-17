"""Turning an LLM provider failure into something a chat user may see.

Deliberately one generic sentence for every cause. Which provider we use, that
its account ran out of credits, that a key was rejected, that we are being rate
limited - none of it is the end user's business, and some of it is information
about our own infrastructure that shouldn't leave the server at all. The real
cause is classified here only so it lands in the logs for whoever is on call.
"""

from app.core.logging import get_logger

log = get_logger(__name__)

# The single message a user ever sees when the model call fails.
GENERIC_LLM_FAILURE = "MUSO is temporarily unavailable. Please try again in a moment."


def _status_code(exc: Exception) -> int | None:
    """Best-effort HTTP status code out of whatever the provider's client raised.

    Covers requests/httpx/openai-style exceptions, which carry it on
    `.response.status_code`, and clients that put it directly on `.status_code`.
    """
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if isinstance(status, int):
        return status

    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status

    return None


def _cause(exc: Exception) -> str:
    """A short operator-facing label for the log line."""
    status = _status_code(exc)
    if status == 402:
        return "provider account out of credits (402)"
    if status == 429:
        return "provider rate limit (429)"
    if status in (401, 403):
        return f"provider rejected our credentials ({status})"
    if status is not None and status >= 500:
        return f"provider server error ({status})"

    exc_type = type(exc).__name__.lower()
    if "timeout" in exc_type:
        return "provider timeout"
    if "connect" in exc_type:
        return "provider unreachable"
    return "unclassified provider failure"


def describe_llm_failure(exc: Exception) -> str:
    """Log what actually went wrong; hand the caller the generic message."""
    log.error("LLM call failed: %s", _cause(exc))
    return GENERIC_LLM_FAILURE
