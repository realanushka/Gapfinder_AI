from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/gapfinder"

    # Auth
    jwt_secret: str = "change-this-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # AI providers
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536
    # Optional separate OpenAI-compatible endpoint for embeddings (e.g. Gemini's
    # free one). If EMBEDDING_BASE_URL is set, EMBEDDING_API_KEY is used for it
    # (falling back to LLM_API_KEY); otherwise OpenAI + OPENAI_API_KEY is used.
    embedding_base_url: str | None = None
    embedding_api_key: str | None = None
    llm_model: str = "claude-sonnet-5"

    # Which backend generates text/JSON: "anthropic" or "openai_compatible".
    # "openai_compatible" covers Google Gemini, Groq, OpenRouter, etc. (all have
    # free tiers) -- set LLM_BASE_URL and LLM_API_KEY for the one you pick.
    llm_provider: str = "anthropic"
    llm_api_key: str | None = None
    llm_base_url: str | None = None

    # App
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"

    # Demo account
    demo_user_email: str = "demo@gapfinder.ai"
    demo_user_password: str = "demo123"

    @property
    def embeddings_configured(self) -> bool:
        if self.embedding_base_url:
            return bool(self.embedding_api_key or self.llm_api_key)
        return bool(self.openai_api_key)

    @field_validator("database_url")
    @classmethod
    def _use_asyncpg_driver(cls, value: str) -> str:
        """Accept the plain `postgresql://` string Supabase shows; we need asyncpg."""
        for prefix in ("postgresql://", "postgres://"):
            if value.startswith(prefix):
                value = "postgresql+asyncpg://" + value[len(prefix):]
                break

        # Supabase appends `?pgbouncer=true`; asyncpg rejects it as a connect() argument.
        base, _, query = value.partition("?")
        if query:
            kept = [part for part in query.split("&") if not part.lower().startswith("pgbouncer=")]
            value = base + ("?" + "&".join(kept) if kept else "")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
