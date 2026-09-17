"""The agent loop: ask the model, run any tool it requests, ask again, answer."""

import re

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from app.agent.llm import get_llm
from app.agent.prompts import SELECTED_LEAD_SUFFIX, SYSTEM_PROMPT
from app.agent.tools import TOOLS, TOOLS_BY_NAME
from app.core.config import settings
from app.core.exceptions import LLMError
from app.core.logging import get_logger

log = get_logger(__name__)


class AgentResult:
    def __init__(self, answer: str, tools_used: list[str]):
        self.answer = answer
        self.tools_used = tools_used


def _extract_status_code(exc: Exception) -> int | None:
    """Best-effort HTTP status code out of whatever the provider's client raised.

    Covers requests/httpx-style exceptions (HuggingFace, most HTTP providers),
    which carry it on `.response.status_code`, and clients that put it directly
    on `.status_code`.
    """
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    if isinstance(status, int):
        return status

    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status

    return None


def _describe_llm_failure(exc: Exception) -> str:
    """A short, user-safe explanation of an LLM call failure.

    The full exception (URLs, request ids, provider-specific detail) is only
    ever logged - a chat user never needs to see any of that, and some of it
    (provider name, account state) shouldn't leave the server anyway.
    """
    status = _extract_status_code(exc)

    if status == 402:
        return (
            "The AI provider account has run out of credits for this month. "
            "Please top up credits (or switch providers) and try again."
        )
    if status == 429:
        return "The AI service is getting too many requests right now. Please wait a moment and try again."
    if status in (401, 403):
        return "The AI service rejected our credentials. Please check the configured API key."
    if status is not None and status >= 500:
        return "The AI service is having problems right now. Please try again shortly."

    exc_type = type(exc).__name__.lower()
    if "timeout" in exc_type:
        return "The AI service took too long to respond. Please try again."
    if "connect" in exc_type:
        return "Could not reach the AI service. Please check the connection and try again."

    return "The AI service could not answer that. Please try again in a moment."


# Some local models (notably smaller ones served through Ollama) occasionally
# emit a tool call as literal text - e.g. `<tool_call>{"name": "get_lead",
# "arguments": {...}` - instead of using the structured function-calling
# format LangChain expects. When that happens `reply.tool_calls` is empty, so
# without this guard the raw (often truncated, mid-JSON) text would be shown
# to the user as if it were a real answer.
_LEAKED_TOOL_CALL_RE = re.compile(r"<tool_call>|\"arguments\"\s*:")

_UNUSABLE_REPLY_MESSAGE = (
    "I couldn't process that properly - could you rephrase it as a plain question? "
    "For example: \"show lead <id>'s history\" or \"who is <name>\"."
)


def _reply_is_unusable(content: str) -> bool:
    """True when the model's plain-text reply is empty, or is really an
    unparsed tool-call attempt that leaked through as content instead of a
    structured tool call (see note above) - either way, it must never reach
    the user as-is.
    """
    text = (content or "").strip()
    if not text:
        return True
    return bool(_LEAKED_TOOL_CALL_RE.search(text))


def run_agent(
    message: str,
    lead_id: str | None = None,
    history: list[BaseMessage] | None = None,
) -> AgentResult:
    llm = get_llm().bind_tools(TOOLS)

    system = SYSTEM_PROMPT
    if lead_id:
        system += SELECTED_LEAD_SUFFIX.format(lead_id=lead_id)

    messages: list[BaseMessage] = [SystemMessage(system)]
    messages += history or []
    messages.append(HumanMessage(message))

    tools_used: list[str] = []

    for _ in range(settings.agent_max_steps):
        try:
            reply: AIMessage = llm.invoke(messages)
        except Exception as exc:  # noqa: BLE001 - any provider failure, reported as one
            log.exception("LLM call failed")
            raise LLMError(_describe_llm_failure(exc)) from exc

        tool_calls = getattr(reply, "tool_calls", None)
        if not tool_calls:
            if _reply_is_unusable(reply.content):
                log.warning("Model reply had no tool call and unusable content: %r", reply.content)
                # Don't let a broken reply sit in this turn's history - if a later
                # step in this same call reads it back, it should see the clean
                # version, not a truncated tool-call fragment.
                messages.append(AIMessage(_UNUSABLE_REPLY_MESSAGE))
                return AgentResult(_UNUSABLE_REPLY_MESSAGE, tools_used)
            messages.append(reply)
            return AgentResult(reply.content, tools_used)

        messages.append(reply)
        for call in tool_calls:
            tool = TOOLS_BY_NAME.get(call["name"])
            if tool is None:
                output = f"Unknown tool: {call['name']}"
            else:
                log.info("tool call: %s %s", call["name"], call["args"])
                try:
                    output = tool.invoke(call["args"])
                    tools_used.append(call["name"])
                except Exception as exc:  # noqa: BLE001 - a bad/incomplete tool call must not crash the turn
                    # E.g. the model called get_lead with a missing or made-up
                    # id: a Pydantic/LangChain validation error here would
                    # otherwise propagate up and fail the whole request. Feed
                    # it back as a normal tool result instead, so the model
                    # gets a chance to recover - retry with a real id, search
                    # by name first, or ask the user - in its next step.
                    log.warning("tool call failed: %s %s (%s)", call["name"], call["args"], exc)
                    output = (
                        f"That call to {call['name']} failed: {exc}. "
                        "If a required value was missing or guessed, get the real "
                        "one (e.g. via search_leads) or ask the user, rather than retrying with a guess."
                    )
            messages.append(ToolMessage(content=str(output), tool_call_id=call["id"]))

    return AgentResult("I could not finish that within the step limit.", tools_used)
