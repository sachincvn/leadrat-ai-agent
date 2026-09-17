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
    llm_provider: str = "ollama"  # ollama | huggingface | local_hf
    llm_temperature: float = 0.1
    llm_max_tokens: int = 800
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    hf_api_token: str = ""
    hf_model: str = "Qwen/Qwen2.5-7B-Instruct"
    local_hf_model: str = "Qwen/Qwen3-8B"
    local_hf_load_4bit: bool = False

    # agent
    agent_max_steps: int = 3

    # crm
    use_mock_crm: bool = True
    leadrat_base_url: str = "https://connect.leadrat.info"
    leadrat_tenant: str = ""  # falls back to the JWT's custom:tenant_id claim
    leadrat_timeout: int = 60
    leadrat_jwt: str = ""  # dev fallback; real calls carry the caller's JWT

    # paths
    mock_data_file: Path = BASE_DIR / "data" / "mock" / "leads.json"

    @property
    def active_model(self) -> str:
        return {
            "ollama": self.ollama_model,
            "huggingface": self.hf_model,
            "local_hf": self.local_hf_model,
        }.get(self.llm_provider, "unknown")

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
