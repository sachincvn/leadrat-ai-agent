"""Local open-source model served by Ollama."""

import inspect

from langchain_core.language_models import BaseChatModel

from app.agent.llm.base import LLMProvider
from app.core.config import settings


class OllamaProvider(LLMProvider):
    def build(self) -> BaseChatModel:
        from langchain_ollama import ChatOllama

        kwargs: dict = {
            "model": settings.ollama_model,
            "base_url": settings.ollama_base_url,
            "temperature": settings.llm_temperature,
            "num_predict": settings.llm_max_tokens,
        }
        # `reasoning` only exists on newer langchain-ollama. On older versions
        # the <think> block is stripped in the agent loop instead, so this is
        # an optimisation, not a requirement.
        if settings.llm_disable_thinking and "reasoning" in inspect.signature(ChatOllama).parameters:
            kwargs["reasoning"] = False

        return ChatOllama(**kwargs)
