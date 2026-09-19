"""Resolves LLM_PROVIDER to a chat model.

Both providers speak the OpenAI protocol and both are picked for the same
reason: native tool calling. There is no fallback between them - the provider
is chosen once in `.env`, and when it is down the turn says so rather than
quietly answering with a model that selects tools differently.
"""

from functools import lru_cache

from langchain_core.language_models import BaseChatModel

from app.agent.llm.base import LLMProvider
from app.agent.llm.groq_provider import GroqProvider
from app.agent.llm.huggingface_provider import HuggingFaceProvider
from app.agent.llm.mistral_provider import MistralProvider
from app.core.config import settings
from app.core.exceptions import LLMError

PROVIDERS: dict[str, type[LLMProvider]] = {
    "huggingface": HuggingFaceProvider,
    "mistral": MistralProvider,
    "groq": GroqProvider,
}


@lru_cache
def get_llm() -> BaseChatModel:
    provider = PROVIDERS.get(settings.llm_provider)
    if provider is None:
        known = ", ".join(sorted(PROVIDERS))
        raise LLMError(f"Unknown LLM_PROVIDER '{settings.llm_provider}' (known: {known})")
    return provider().build()
