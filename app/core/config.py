"""Environment-backed settings. Single source of truth for configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    # app
    app_name: str = "MUSO AI"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    cors_origins: str = "*"

    # llm
    llm_provider: str = "huggingface"  # huggingface | mistral
    llm_temperature: float = 0.1
    llm_max_tokens: int = 1500
    # Reasoning models (Qwen3, DeepSeek-R1, ...) spend most of their latency
    # emitting a <think> block nobody reads. Tool selection here is decided by
    # the prompt, not by chain-of-thought, so thinking is off by default.
    llm_disable_thinking: bool = True
    llm_timeout: int = 90
    hf_api_token: str = ""
    hf_model: str = "Qwen/Qwen3-235B-A22B-Instruct-2507"
    # OpenAI-compatible HF router: native tool calling, much faster and far
    # more reliable than the raw text-generation endpoint.
    hf_base_url: str = "https://router.huggingface.co/v1"
    mistral_api_key: str = ""
    mistral_model: str = "mistral-large-latest"
    # La Plateforme is OpenAI-compatible, so it reuses the same client.
    mistral_base_url: str = "https://api.mistral.ai/v1"

    # agent
    agent_max_steps: int = 5

    # crm - the caller's JWT and tenant arrive per request, never from here
    leadrat_base_url: str = "https://connect.leadrat.info/api/v1/mcp"
    leadrat_timeout: int = 60


    @property
    def active_model(self) -> str:
        return {
            "huggingface": self.hf_model,
            "mistral": self.mistral_model,
        }.get(self.llm_provider, "unknown")

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
