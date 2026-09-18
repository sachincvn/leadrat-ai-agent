"""Stateless single-lead Q&A: lead history in, one structured analysis out.

Deliberately outside the tool-calling agent loop in app/agent/runner.py - the
lead id is already known from the URL, so the model never needs to choose or
call a tool itself. It only ever sees this one lead's history, and nothing
about the turn (message, history or answer) is written anywhere - there is no
session key, so there is nothing to key a store by.

The response is asked for as structured output (Ollama's json_schema format,
via LangChain's with_structured_output) rather than free text, so
LeadPriority/LeadStatus/LeadStage/KeyHighlights come back as real fields an
agent can read directly instead of prose it would have to re-parse.
"""

import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.llm import get_llm
from app.agent.llm.errors import describe_llm_failure
from app.agent.prompts import (
    DEFAULT_LEAD_CHAT_MESSAGE,
    LEAD_CHAT_SYSTEM_PROMPT,
    LEAD_CHAT_USER_PROMPT,
)
from app.agent.runner import strip_thinking
from app.agent.sanitize import strip_internal_ids
from app.api.deps import Caller
from app.core.context import use_caller
from app.core.exceptions import LLMError
from app.core.logging import get_logger
from app.integrations.crm.factory import get_crm_client
from app.schemas.lead_chat import LeadChatRequest, LeadChatResponse

log = get_logger(__name__)

HISTORY_LIMIT = 15

_NO_ANSWER = "I couldn't find anything relevant for this lead."

# Belt-and-braces for a small model that ignores the "no bullets" instruction:
# a leading bullet/number marker on any line, and the line breaks between
# them, are what turn a paragraph into a list - strip both.
_LIST_MARKER = re.compile(r"^[ \t]*(?:[-*•]|\d+[.)])[ \t]+", re.MULTILINE)


def _as_paragraph(text: str) -> str:
    text = _LIST_MARKER.sub("", text)
    return re.sub(r"\s*\n+\s*", " ", text).strip()


def handle_lead_chat(lead_id: str, request: LeadChatRequest, caller: Caller) -> LeadChatResponse:
    with use_caller(caller.jwt, caller.tenant):
        history = get_crm_client().get_lead_history(lead_id, limit=HISTORY_LIMIT)

    lead_history_text = "\n".join(
        entry.model_dump_json(exclude_none=True) for entry in history.entries
    ) or "No history is available for this lead."

    user_message = (request.message or "").strip() or DEFAULT_LEAD_CHAT_MESSAGE

    prompt = LEAD_CHAT_USER_PROMPT.format(
        lead_id=lead_id,
        lead_history=lead_history_text,
        user_message=user_message,
    )

    structured_llm = get_llm().with_structured_output(LeadChatResponse)

    try:
        result = structured_llm.invoke(
            [SystemMessage(LEAD_CHAT_SYSTEM_PROMPT), HumanMessage(prompt)]
        )
    except Exception as exc:  # noqa: BLE001 - any provider failure, reported as one
        log.exception("Lead chat LLM call failed")
        raise LLMError(describe_llm_failure(exc)) from exc

    if not isinstance(result, LeadChatResponse):
        result = LeadChatResponse.model_validate(result)

    message = strip_internal_ids(strip_thinking(result.Message)).strip()
    result.Message = _as_paragraph(message) or _NO_ANSWER
    return result
