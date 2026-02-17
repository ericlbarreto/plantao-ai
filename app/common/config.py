"""Application settings loaded from .env via pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration – reads from environment / .env file."""

    APP_ENV: str = "development"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = ""

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # OpenTelemetry / LangSmith
    OTEL_SERVICE_NAME: str = "plantao-ai"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "https://api.smith.langchain.com/otel"
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "plantao-ai"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


# Singleton used across the app
settings = Settings()
