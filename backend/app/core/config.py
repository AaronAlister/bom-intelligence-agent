from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    # Application
    app_name: str = "BOM Intelligence Agent"
    app_env: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    # PostgreSQL
    database_url: str = (
        "postgresql+asyncpg://"
        "bom_admin:change_me@postgres:5432/"
        "bom_intelligence"
    )

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # RAG / Embeddings
    embedding_provider: str = "deterministic"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    openai_api_key: str = ""

    # Qdrant
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "bom_documents"

    # LLM
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # Mouser Search API
    mouser_api_key: str = ""
    mouser_api_base_url: str = (
        "https://api.mouser.com/api/v1"
    )
    mouser_api_timeout_seconds: float = 15.0

    # Arrow Pricing & Availability API
    arrow_api_login: str = ""
    arrow_api_key: str = ""
    arrow_api_base_url: str = "https://api.arrow.com"
    arrow_api_timeout_seconds: float = 15.0

    # Digi-Key Product Information API
    digikey_client_id: str = ""
    digikey_client_secret: str = ""
    digikey_api_base_url: str = (
        "https://api.digikey.com"
    )
    digikey_api_timeout_seconds: float = 15.0
    digikey_locale_site: str = "IN"
    digikey_locale_language: str = "en"
    digikey_locale_currency: str = "INR"

    # Security
    secret_key: str = "change-me"

    # Upload limits
    max_bom_file_size_mb: int = 25

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_security(
        self,
    ) -> "Settings":
        """
        Prevent unsafe placeholder secrets from being
        used when the application runs in production.
        """

        if self.app_env.lower() == "production":
            if self.secret_key in {
                "",
                "change-me",
                "change_me",
                "replace_with_a_long_random_secret",
            }:
                raise ValueError(
                    "SECRET_KEY must be configured with "
                    "a secure value in production."
                )

            if "change_me" in self.database_url:
                raise ValueError(
                    "DATABASE_URL must not use the "
                    "default database password in production."
                )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()