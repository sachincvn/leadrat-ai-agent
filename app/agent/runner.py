"""The agent loop: ask the model, run any tool it requests, ask again, answer."""

import json
import re
from collections.abc import Iterator

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from app.agent.genui import render_blocks
from app.agent.llm import get_llm
from app.agent.llm.errors import describe_llm_failure
from app.agent.prompts import (
    BLOCKS_RENDERED_SUFFIX,
    RECENT_DATA_SUFFIX,
    SELECTED_LEAD_SUFFIX,
    SYSTEM_PROMPT,
    TODAY_SUFFIX,
)
from app.agent.sanitize import strip_internal_ids
from app.agent.streaming import SafeAnswerStream
from app.agent.tools import TOOLS, TOOLS_BY_NAME
from app.core.clock import describe_today, today_iso
from app.core.config import settings
from app.core.exceptions import LLMError
from app.core.logging import get_logger

log = get_logger(__name__)


class AgentResult:
    def __init__(self, answer: str, tools_used: list[str], tool_notes: list[str] | None = None):
        self.answer = answer
        self.tools_used = tools_used
        # What the tools actually returned this turn, trimmed. The next turn
        # gets these back so a follow-up ("the second one", "call him") can
        # resolve against the real records instead of only the prose answer.
        self.tool_notes = tool_notes or []


# Some local models (notably smaller ones served through Ollama) occasionally
# emit a tool call as literal text - e.g. `<tool_call>{"name": "get_lead",
# "arguments": {...}` - instead of using the structured function-calling
# format LangChain expects. When that happens `reply.tool_calls` is empty, so
# without this guard the raw (often truncated, mid-JSON) text would be shown
# to the user as if it were a real answer.
_LEAKED_TOOL_CALL_RE = re.compile(r"<tool_call>|\"arguments\"\s*:")

# Reasoning models (Qwen3, DeepSeek-R1, ...) wrap their chain of thought in
# <think>...</think>. Thinking is disabled at the provider where the backend
# supports it, but a model served without that switch - or one cut off before
# closing the tag - would otherwise show its scratchpad to the user.
_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_UNCLOSED_THINK_RE = re.compile(r"<think>.*\Z", re.DOTALL | re.IGNORECASE)

# How much of one tool result is carried into the next turn. Enough to keep
# ids and names resolvable, small enough not to grow the prompt unchecked.
TOOL_NOTE_CHARS = 700

# How much of one tool call's arguments is carried with it. The arguments are
# what a follow-up narrows - "show me the new ones" means the previous filter
# plus a status - so the next turn cannot reproduce the result without them.
TOOL_ARGS_CHARS = 400


def _tool_note(call: dict, output: str) -> str:
    """One line of "what was asked, and what came back"."""
    args = json.dumps(call.get("args") or {}, default=str)[:TOOL_ARGS_CHARS]
    return f"{call['name']}({args}) -> {output[:TOOL_NOTE_CHARS]}"


def strip_thinking(content: str) -> str:
    text = _THINK_BLOCK_RE.sub("", content or "")
    text = _UNCLOSED_THINK_RE.sub("", text)
    return text.strip()


_UNUSABLE_REPLY_MESSAGE = "I couldn't process that properly"


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


def _build_messages(
    message: str,
    lead_id: str | None,
    history: list[BaseMessage] | None,
    recent_tool_notes: list[str] | None,
    renders_blocks: bool = False,
) -> list[BaseMessage]:
    system = SYSTEM_PROMPT + TODAY_SUFFIX.format(
        today=describe_today(), today_iso=today_iso()
    )
    if renders_blocks:
        system += BLOCKS_RENDERED_SUFFIX
    if lead_id:
        system += SELECTED_LEAD_SUFFIX.format(lead_id=lead_id)
    if recent_tool_notes:
        system += RECENT_DATA_SUFFIX.format(data="\n".join(recent_tool_notes))

    messages: list[BaseMessage] = [SystemMessage(system)]
    messages += history or []
    messages.append(HumanMessage(message))
    return messages


def _run_tool(call: dict, failures: list[str] | None = None) -> str:
    """One tool call, with a failure fed back to the model rather than raised.

    `failures` collects the reason for each failed call so that a turn which
    runs out of steps can say what actually went wrong instead of blaming the
    step limit, which tells the user nothing they can act on.
    """
    tool = TOOLS_BY_NAME.get(call["name"])
    if tool is None:
        if failures is not None:
            failures.append(f"unknown tool {call['name']}")
        return f"Unknown tool: {call['name']}"

    log.info("tool call: %s %s", call["name"], call["args"])
    try:
        return str(tool.invoke(call["args"]))
    except Exception as exc:  # noqa: BLE001 - a bad/incomplete tool call must not crash the turn
        # E.g. the model called get_lead with a missing or made-up id: a
        # Pydantic/LangChain validation error here would otherwise propagate
        # up and fail the whole request. Feed it back as a normal tool result
        # instead, so the model gets a chance to recover - retry with a real
        # id, search by name first, or ask the user - in its next step.
        log.warning("tool call failed: %s %s (%s)", call["name"], call["args"], exc)
        if failures is not None:
            failures.append(str(exc))
        return (
            f"That call to {call['name']} failed: {exc}. "
            "If a required value was missing or guessed, get the real "
            "one (e.g. via search_leads) or ask the user, rather than retrying with a guess."
        )


def run_agent(
    message: str,
    lead_id: str | None = None,
    history: list[BaseMessage] | None = None,
    recent_tool_notes: list[str] | None = None,
) -> AgentResult:
    llm = get_llm().bind_tools(TOOLS)
    messages = _build_messages(message, lead_id, history, recent_tool_notes)

    tools_used: list[str] = []
    tool_notes: list[str] = []
    failures: list[str] = []

    for _ in range(settings.agent_max_steps):
        try:
            reply: AIMessage = llm.invoke(messages)
        except Exception as exc:  # noqa: BLE001 - any provider failure, reported as one
            raise LLMError(describe_llm_failure(exc)) from exc

        tool_calls = getattr(reply, "tool_calls", None)
        if not tool_calls:
            raw = reply.content if isinstance(reply.content, str) else str(reply.content)
            answer = strip_internal_ids(strip_thinking(raw))
            if _reply_is_unusable(answer):
                log.warning("Model reply had no tool call and unusable content: %r", reply.content)
                # Don't let a broken reply sit in this turn's history - if a later
                # step in this same call reads it back, it should see the clean
                # version, not a truncated tool-call fragment.
                messages.append(AIMessage(_UNUSABLE_REPLY_MESSAGE))
                return AgentResult(_UNUSABLE_REPLY_MESSAGE, tools_used, tool_notes)
            messages.append(AIMessage(answer))
            return AgentResult(answer, tools_used, tool_notes)

        messages.append(reply)
        for call in tool_calls:
            output = _run_tool(call, failures)
            if call["name"] in TOOLS_BY_NAME:
                tools_used.append(call["name"])
            messages.append(ToolMessage(content=output, tool_call_id=call["id"]))
            tool_notes.append(_tool_note(call, output))

    return AgentResult(_incomplete_answer(failures), tools_used, tool_notes)


STEP_LIMIT_MESSAGE = (
    "I could not finish that - I ran out of steps before I had an answer."
)


def _incomplete_answer(failures: list[str]) -> str:
    """What to say when the loop ends with no answer.

    A bare "step limit" line reads like the assistant gave up for no reason. If
    the steps were spent on calls the CRM rejected, the last rejection is the
    honest explanation, and the only one the user could act on.
    """
    if not failures:
        return STEP_LIMIT_MESSAGE
    return (
        "I could not complete that - the CRM rejected the request. "
        f"Last error: {failures[-1]}"
    )


# ---------------------------------------------------------------- streaming


class StreamEvent:
    """One thing worth telling the client about, mid-turn.

    kind is one of:
      "status" - a tool is running, so the UI can say what MUSO is doing
      "block"  - a renderable block built from a tool result (see agent/genui)
      "text"   - display-ready text to append to the answer
      "done"   - the turn finished; carries the full answer and tools used
    """

    def __init__(self, kind: str, **data) -> None:
        self.kind = kind
        self.data = data


def stream_agent(
    message: str,
    lead_id: str | None = None,
    history: list[BaseMessage] | None = None,
    recent_tool_notes: list[str] | None = None,
    renders_blocks: bool = False,
) -> Iterator[StreamEvent]:
    """The same loop as run_agent, emitting the answer as it is generated.

    Only the final, non-tool-calling step is streamed to the user. The steps
    that call tools produce no prose worth showing - just a status event so
    the wait is explained rather than silent.
    """
    llm = get_llm().bind_tools(TOOLS)
    messages = _build_messages(
        message, lead_id, history, recent_tool_notes, renders_blocks
    )

    tools_used: list[str] = []
    tool_notes: list[str] = []
    failures: list[str] = []

    for _ in range(settings.agent_max_steps):
        safe = SafeAnswerStream()
        answer_parts: list[str] = []
        reply: AIMessage | None = None

        try:
            for chunk in llm.stream(messages):
                # Chunks accumulate into one message, which is how a tool call
                # split across several chunks becomes a whole tool call.
                reply = chunk if reply is None else reply + chunk
                piece = chunk.content if isinstance(chunk.content, str) else ""
                for text in safe.feed(piece):
                    answer_parts.append(text)
                    yield StreamEvent("text", text=text)
        except Exception as exc:  # noqa: BLE001 - any provider failure, reported as one
            # A stream that has already started cannot become an HTTP error, and
            # a half-written answer followed by nothing is worse than a sentence
            # saying so. The turn ends normally, carrying the failure message.
            notice = describe_llm_failure(exc)
            partial = "".join(answer_parts).strip()
            answer = partial + "\n\n" + notice if partial else notice
            yield StreamEvent("text", text=notice)
            yield StreamEvent(
                "done", answer=answer, tools_used=tools_used, tool_notes=tool_notes
            )
            return

        tool_calls = getattr(reply, "tool_calls", None) if reply is not None else None

        if not tool_calls:
            for text in safe.flush():
                answer_parts.append(text)
                yield StreamEvent("text", text=text)

            answer = "".join(answer_parts).strip()
            if not safe.produced_output or _reply_is_unusable(answer):
                log.warning("Model reply had no tool call and unusable content: %r", answer)
                answer = _UNUSABLE_REPLY_MESSAGE
                yield StreamEvent("text", text=answer)

            yield StreamEvent("done", answer=answer, tools_used=tools_used, tool_notes=tool_notes)
            return

        # A tool-calling step: nothing shown so far belongs in the answer.
        messages.append(reply)
        for call in tool_calls:
            yield StreamEvent("status", tool=call["name"])
            output = _run_tool(call, failures)
            if call["name"] in TOOLS_BY_NAME:
                tools_used.append(call["name"])
            messages.append(ToolMessage(content=output, tool_call_id=call["id"]))
            tool_notes.append(_tool_note(call, output))
            # The data is on screen before the model has finished describing
            # it, and it is the tool's own output - not something the model
            # re-typed, and so not something it can get wrong.
            for block in render_blocks(call["name"], output):
                yield StreamEvent("block", name=block.name, props=block.props)

    answer = _incomplete_answer(failures)
    yield StreamEvent("text", text=answer)
    yield StreamEvent("done", answer=answer, tools_used=tools_used, tool_notes=tool_notes)
