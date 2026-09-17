"""The chat model MUSO runs on: Qwen on the Hugging Face router, and nothing else.

One provider on purpose. A fallback chain would mean a second model answering
with different tool-calling behaviour on the days the first one is unavailable,
which is worse than a clear "try again in a moment" - the failure stays visible
instead of quietly degrading every answer.
"""

from functools import lru_cache

from langchain_core.language_models import BaseChatModel

from app.agent.llm.huggingface_provider import HuggingFaceProvider


@lru_cache
def get_llm() -> BaseChatModel:
    return HuggingFaceProvider().build()
