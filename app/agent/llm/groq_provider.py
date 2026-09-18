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

        return ChatOpenAI(
            model=settings.groq_model,
            base_url=settings.groq_base_url,
            api_key=settings.groq_api_key,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout,
            max_retries=1,
        )
