"""Resolves LLM_PROVIDER to a chat model. Add new providers to the registry."""

from functools import lru_cache

from langchain_core.language_models import BaseChatModel

from app.agent.llm.base import LLMProvider
from app.agent.llm.huggingface_provider import HuggingFaceProvider
from app.agent.llm.local_hf_provider import LocalHFProvider
from app.agent.llm.ollama_provider import OllamaProvider
from app.core.config import settings
from app.core.exceptions import LLMError

PROVIDERS: dict[str, type[LLMProvider]] = {
    "ollama": OllamaProvider,
    "huggingface": HuggingFaceProvider,
    "local_hf": LocalHFProvider,
}


@lru_cache
def get_llm() -> BaseChatModel:
    provider = PROVIDERS.get(settings.llm_provider)
    if provider is None:
        raise LLMError(f"Unknown LLM_PROVIDER '{settings.llm_provider}'")
    return provider().build()
