"""Hosted open-source model via the Hugging Face router (OpenAI-compatible).

The router speaks the OpenAI chat-completions protocol, so tool calls come back
as structured `tool_calls` instead of text the agent has to parse out of a
completion. That is both faster and far more reliable than the plain
text-generation endpoint, which re-renders the whole chat template on every
turn and regularly leaks `<tool_call>` fragments into the answer.

Thinking models are told to skip the <think> block via `chat_template_kwargs`,
which vLLM/TGI forward into the model's chat template.
"""

from langchain_core.language_models import BaseChatModel

from app.agent.llm.base import LLMProvider
from app.core.config import settings
from app.core.exceptions import LLMError


class HuggingFaceProvider(LLMProvider):
    def build(self) -> BaseChatModel:
        from langchain_openai import ChatOpenAI

        if not settings.hf_api_token:
            raise LLMError("HF_API_TOKEN is not set")

        extra_body: dict = {}
        if settings.llm_disable_thinking:
            # Qwen3 / DeepSeek naming differs; sending both is harmless - a
            # template that doesn't know a key ignores it.
            extra_body["chat_template_kwargs"] = {"enable_thinking": False, "thinking": False}

        return ChatOpenAI(
            model=settings.hf_model,
            base_url=settings.hf_base_url,
            api_key=settings.hf_api_token,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout,
            max_retries=1,
            extra_body=extra_body or None,
        )
