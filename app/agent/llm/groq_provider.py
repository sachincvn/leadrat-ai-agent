"""Groq's hosted models, over their OpenAI-compatible endpoint.

Groq serves open-weight models (Llama, Qwen, Kimi) on its own inference
hardware, which is the fastest of the three providers here by a wide margin -
useful when a turn costs several model calls, as a tool-calling turn always
does.

The endpoint speaks the OpenAI chat-completions protocol, so the same
`langchain-openai` client the other two use works with a different base URL,
and tool calls arrive as structured `tool_calls`. As with Mistral, it does not
accept `chat_template_kwargs` - that is a vLLM/TGI extension the HF router
forwards into the template - so the thinking switch is not applied here.
"""

from langchain_core.language_models import BaseChatModel

from app.agent.llm.base import LLMProvider
from app.core.config import settings
from app.core.exceptions import LLMError


class GroqProvider(LLMProvider):
    def build(self) -> BaseChatModel:
        from langchain_openai import ChatOpenAI

        if not settings.groq_api_key:
            raise LLMError("GROQ_API_KEY is not set")

        extra_body: dict = {}
        if settings.groq_model.startswith("openai/gpt-oss"):
            # Reasoning tokens are spent from the same max_tokens budget as the
            # answer, and arrive in the reply unless told otherwise. Hiding
            # them keeps a chain of thought off the user's screen, and keeping
            # the effort low keeps the budget for the answer - tool selection
            # here is a prompt decision, not something to deliberate over.
            extra_body["reasoning_format"] = "hidden"
            extra_body["reasoning_effort"] = settings.groq_reasoning_effort

        return ChatOpenAI(
            model=settings.groq_model,
            base_url=settings.groq_base_url,
            api_key=settings.groq_api_key,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout,
            max_retries=1,
            extra_body=extra_body or None,
        )
