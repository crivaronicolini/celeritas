import secrets
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=False,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    PROJECT_NAME: str
    VECTOR_DB_PATH: str
    DOC_DIR_PATH: str
    DATABASE_URL: str
    OPENAI_API_KEY: SecretStr
    LANGSMITH_API_KEY: SecretStr
    LANGSMITH_TRACING: bool = True


settings = Settings()  # type: ignore
