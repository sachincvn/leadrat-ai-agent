"""The agent loop: ask the model, run any tool it requests, ask again, answer."""

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from app.agent.llm import get_llm
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import TOOLS, TOOLS_BY_NAME
from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


class AgentResult:
    def __init__(self, answer: str, tools_used: list[str]):
        self.answer = answer
        self.tools_used = tools_used


def run_agent(
    message: str,
    lead_id: str | None = None,
    history: list[BaseMessage] | None = None,
) -> AgentResult:
    llm = get_llm().bind_tools(TOOLS)

    messages: list[BaseMessage] = [SystemMessage(SYSTEM_PROMPT.format(lead_id=lead_id or "none"))]
    messages += history or []
    messages.append(HumanMessage(message))

    tools_used: list[str] = []

    for _ in range(settings.agent_max_steps):
        reply: AIMessage = llm.invoke(messages)
        messages.append(reply)

        tool_calls = getattr(reply, "tool_calls", None)
        if not tool_calls:
            return AgentResult(reply.content, tools_used)

        for call in tool_calls:
            tool = TOOLS_BY_NAME.get(call["name"])
            if tool is None:
                output = f"Unknown tool: {call['name']}"
            else:
                log.info("tool call: %s %s", call["name"], call["args"])
                output = tool.invoke(call["args"])
                tools_used.append(call["name"])
            messages.append(ToolMessage(content=str(output), tool_call_id=call["id"]))

    return AgentResult("I could not finish that within the step limit.", tools_used)
