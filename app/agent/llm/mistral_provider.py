"""Mistral's hosted models, over their OpenAI-compatible endpoint.

La Plateforme speaks the OpenAI chat-completions protocol, so the same
`langchain-openai` client the HF router uses works here with a different base
URL - no extra dependency, and tool calls arrive as structured `tool_calls`.

Mistral's models are trained for function calling and are noticeably stricter
about it than a general chat model: they return an empty content string with
the call rather than narrating it, which is exactly what this agent's loop
wants. What they do not accept is `chat_template_kwargs` - that is a vLLM/TGI
extension the HF router forwards into the template, and sending it here is a
400, so the thinking switch is simply not applied.
"""

from langchain_core.language_models import BaseChatModel

from app.agent.llm.base import LLMProvider
from app.core.config import settings
from app.core.exceptions import LLMError


class MistralProvider(LLMProvider):
    def build(self) -> BaseChatModel:
        from langchain_openai import ChatOpenAI

        if not settings.mistral_api_key:
            raise LLMError("MISTRAL_API_KEY is not set")

        return ChatOpenAI(
            model=settings.mistral_model,
            base_url=settings.mistral_base_url,
            api_key=settings.mistral_api_key,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout,
            max_retries=1,
        )
