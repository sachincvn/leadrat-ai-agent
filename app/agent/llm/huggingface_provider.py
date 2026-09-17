"""Hosted open-source model via the Hugging Face Inference API."""

from langchain_core.language_models import BaseChatModel

from app.agent.llm.base import LLMProvider
from app.core.config import settings
from app.core.exceptions import LLMError


class HuggingFaceProvider(LLMProvider):
    def build(self) -> BaseChatModel:
        from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

        if not settings.hf_api_token:
            raise LLMError("HF_API_TOKEN is not set")

        endpoint = HuggingFaceEndpoint(
            repo_id=settings.hf_model,
            huggingfacehub_api_token=settings.hf_api_token,
            task="text-generation",
            temperature=settings.llm_temperature,
            max_new_tokens=settings.llm_max_tokens,
        )
        return ChatHuggingFace(llm=endpoint)
