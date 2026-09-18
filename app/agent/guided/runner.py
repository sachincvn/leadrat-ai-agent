"""The capability-aware agent loop.

Same shape as app/agent/runner.py, with one structural difference: this loop can
stop half-way. CRM tools run here and the loop continues; UI actions cannot run
here at all, so when the model calls one the loop returns the plan and waits for
the browser to report back on the next request.

The read-only chat loop in app/agent/runner.py is untouched and still serves
/api/v1/chat.
"""

import json

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from app.agent.guided.prompts import build_system_prompt
from app.agent.guided.registry import ACTIONS_BY_NAME
from app.agent.guided.resolver import resolve, ui_tools
from app.agent.llm import get_llm
from app.agent.prompts import SELECTED_LEAD_SUFFIX
from app.agent.tools import TOOLS, TOOLS_BY_NAME
from app.core.config import settings
from app.agent.llm.errors import describe_llm_failure
from app.agent.sanitize import strip_internal_ids
from app.core.exceptions import LLMError
from app.core.logging import get_logger
from app.schemas.assistant import (
    AssistantTurnRequest,
    AssistantTurnResponse,
    PlanItem,
    RejectedCall,
    ToolCall,
    ToolResult,
    TranscriptEntry,
)

log = get_logger(__name__)


def _to_langchain(history: list[TranscriptEntry]) -> list[BaseMessage]:
    """Shared transcript -> provider messages."""
    messages: list[BaseMessage] = []
    for entry in history:
        if entry.role == "user":
            messages.append(HumanMessage(entry.text))
        elif entry.role == "assistant":
            messages.append(
                AIMessage(
                    content=entry.text,
                    tool_calls=[
                        {"id": c.id, "name": c.name, "args": c.args} for c in entry.tool_calls
                    ],
                )
            )
        elif entry.role == "tool":
            for result in entry.results:
                messages.append(ToolMessage(content=result.content, tool_call_id=result.id))
    return messages


def run_turn(request: AssistantTurnRequest) -> AssistantTurnResponse:
    can_drive_ui = request.can_drive_ui

    tools = [*TOOLS, *ui_tools()] if can_drive_ui else list(TOOLS)
    llm = get_llm().bind_tools(tools)

    system = build_system_prompt(
        can_drive_ui=can_drive_ui,
        page_context=json.dumps(request.page_context, default=str, indent=2)
        if request.page_context
        else None,
    )
    if request.lead_id:
        system += SELECTED_LEAD_SUFFIX.format(lead_id=request.lead_id)

    messages: list[BaseMessage] = [SystemMessage(system)]
    messages += _to_langchain(request.history)

    # Everything this turn adds to the transcript, returned so the client can
    # replay exactly what the model saw on the next request.
    appended: list[TranscriptEntry] = []

    if request.message:
        messages.append(HumanMessage(request.message))
        appended.append(TranscriptEntry(role="user", text=request.message))
    if request.tool_results:
        for result in request.tool_results:
            # What the browser actually did is the only account of a flow that
            # exists: the steps run out there, and until this was logged a
            # walkthrough that failed silently looked, from here, exactly like
            # one that worked.
            log.info(
                "step result%s: %s",
                " (FAILED)" if result.is_error else "",
                result.content[:400],
            )
            messages.append(ToolMessage(content=result.content, tool_call_id=result.id))
        appended.append(TranscriptEntry(role="tool", results=request.tool_results))

    tools_used: list[str] = []

    for _ in range(settings.assistant_max_steps):
        try:
            reply: AIMessage = llm.invoke(messages)
        except Exception as exc:  # noqa: BLE001 - any provider failure, reported as one
            log.exception("LLM call failed")
            raise LLMError(describe_llm_failure(exc)) from exc

        messages.append(reply)
        calls = getattr(reply, "tool_calls", None) or []
        text = reply.content if isinstance(reply.content, str) else str(reply.content)
        text = strip_internal_ids(text)

        appended.append(
            TranscriptEntry(
                role="assistant",
                text=text,
                tool_calls=[
                    ToolCall(id=c["id"], name=c["name"], args=c.get("args") or {}) for c in calls
                ],
            )
        )

        if not calls:
            return AssistantTurnResponse(
                type="message",
                text=text,
                tools_used=tools_used,
                history_append=appended,
            )

        plan: list[PlanItem] = []
        rejected: list[RejectedCall] = []
        server_results: list[ToolResult] = []

        for call in calls:
            name, call_id = call["name"], call["id"]

            # A UI action: the browser owns it. Validate and expand it here so a
            # bad generation never reaches the DOM.
            action = ACTIONS_BY_NAME.get(name)
            if action is not None:
                item, error = resolve(call_id, action, call.get("args") or {})
                if error:
                    rejected.append(RejectedCall(call_id=call_id, error=error))
                else:
                    plan.append(PlanItem(**item.as_dict()))
                    tools_used.append(name)
                continue

            # A CRM tool: runs here, and the loop continues with its output.
            tool = TOOLS_BY_NAME.get(name)
            if tool is None:
                server_results.append(
                    ToolResult(id=call_id, content=f"Unknown tool: {name}", is_error=True)
                )
                continue

            log.info("tool call: %s %s", name, call.get("args"))
            try:
                output = str(tool.invoke(call.get("args") or {}))
            except Exception as exc:  # noqa: BLE001 - surfaced to the model, not the user
                log.exception("tool %s failed", name)
                output = f"failed: {exc}"
                server_results.append(ToolResult(id=call_id, content=output, is_error=True))
                continue
            tools_used.append(name)
            server_results.append(ToolResult(id=call_id, content=output))

        # Anything for the browser ends the turn. Server-side results from the
        # same reply ride along so the client replays them in the right order.
        if plan:
            # The steps the browser is about to run, so a flow that goes wrong
            # can be read against what it was told to do.
            for item in plan:
                log.info(
                    "plan %s(%s): %s",
                    item.action,
                    item.args,
                    " | ".join(
                        f"{step.type} {step.target or step.to or ''}"
                        f"{'=' + step.value if step.value else ''}".strip()
                        for step in item.steps
                    ),
                )

        if plan or rejected:
            if server_results:
                messages += [
                    ToolMessage(content=r.content, tool_call_id=r.id) for r in server_results
                ]
                appended.append(TranscriptEntry(role="tool", results=server_results))
            return AssistantTurnResponse(
                type="plan",
                text=text,
                plan=plan,
                rejected=rejected,
                tools_used=tools_used,
                history_append=appended,
            )

        messages += [ToolMessage(content=r.content, tool_call_id=r.id) for r in server_results]
        appended.append(TranscriptEntry(role="tool", results=server_results))

    # Out of steps. Saying so and stopping tells the user nothing they can act
    # on, so the answer names what was actually being done - and the log
    # carries it, because a turn that runs this long is usually a loop.
    log.warning("assistant turn hit the step limit after tools: %s", tools_used)
    tried = ", ".join(dict.fromkeys(tools_used)) or "nothing"
    return AssistantTurnResponse(
        type="message",
        text=(
            f"I got stuck part way through that - I tried {tried} and did not "
            "get to the end. Nothing was left half done on screen. Try asking "
            "for the one thing you want changed."
        ),
        tools_used=tools_used,
        history_append=appended,
    )
