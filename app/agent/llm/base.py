"""LLM provider contract — each provider returns a LangChain chat model."""

from abc import ABC, abstractmethod

from langchain_core.language_models import BaseChatModel


class LLMProvider(ABC):
    @abstractmethod
    def build(self) -> BaseChatModel: ...
