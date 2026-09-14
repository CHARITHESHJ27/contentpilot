"""Environment-driven configuration using Pydantic Settings.

All secrets and tunables are loaded from environment variables.
Never hard-code API keys or connection strings.
"""

from enum import Enum
from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class AppEnvironment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LLMProvider(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    HYBRID = "hybrid"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- Application ---
    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # --- LLM ---
    llm_provider: LLMProvider = LLMProvider.HYBRID

    # Gemini (Primary)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    # OpenAI (Fallback)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    enable_fallback: bool = True

    # Ollama (Local)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # Common
    llm_model: str = "gemini-3.5-flash"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 4096

    @model_validator(mode="after")
    def resolve_llm_model(self) -> "Settings":
        if self.llm_provider == LLMProvider.OLLAMA:
            self.llm_model = self.ollama_model
        elif self.llm_provider == LLMProvider.OPENAI:
            self.llm_model = self.openai_model
        elif self.llm_provider == LLMProvider.GEMINI:
            self.llm_model = self.gemini_model
        return self

    # --- Embedding ---
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # --- PostgreSQL ---
    database_url: str = "postgresql+asyncpg://contentpilot:contentpilot@localhost:5432/contentpilot"

    # --- Content Generation ---
    max_retries: int = 2
    max_input_length: int = 4000
    max_output_tokens: int = 8192

    # --- Retrieval ---
    retrieval_top_k: int = 5
    chunk_size: int = 512
    chunk_overlap: int = 64

    # --- Observability ---
    tracing_enabled: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "contentpilot"
    otel_exporter_endpoint: str = ""

    # --- Security ---
    api_rate_limit: int = 10
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def is_development(self) -> bool:
        return self.app_env == AppEnvironment.DEVELOPMENT

    @property
    def database_url_sync(self) -> str:
        """Synchronous database URL for Alembic migrations."""
        return self.database_url.replace("asyncpg", "psycopg2")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton (reads .env)."""
    return Settings()
