"""Local Hugging Face weights loaded in-process with transformers.

Runs a model such as Qwen/Qwen3-8B straight from the Hub — no Ollama, no API.
Needs a real GPU: roughly 16 GB VRAM at bf16, or ~6 GB with LOCAL_HF_LOAD_4BIT=true.
Below that the model spills to CPU and answers take minutes.

Extra dependencies (not in requirements.txt by default — they are large):
    pip install torch --index-url https://download.pytorch.org/whl/cu124
    pip install transformers accelerate bitsandbytes
"""

from langchain_core.language_models import BaseChatModel

from app.agent.llm.base import LLMProvider
from app.core.config import settings
from app.core.exceptions import LLMError


class LocalHFProvider(LLMProvider):
    def build(self) -> BaseChatModel:
        try:
            import torch
            from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
        except ImportError as exc:
            raise LLMError(
                "Local HF provider needs: pip install torch transformers accelerate"
            ) from exc

        model_kwargs: dict = {"device_map": "auto"}
        if settings.local_hf_load_4bit:
            model_kwargs["load_in_4bit"] = True
        else:
            model_kwargs["dtype"] = torch.bfloat16

        pipeline = HuggingFacePipeline.from_model_id(
            model_id=settings.local_hf_model,
            task="text-generation",
            model_kwargs=model_kwargs,
            pipeline_kwargs={
                "max_new_tokens": settings.llm_max_tokens,
                "temperature": settings.llm_temperature,
                "do_sample": settings.llm_temperature > 0,
                "return_full_text": False,
            },
        )
        return ChatHuggingFace(llm=pipeline)
