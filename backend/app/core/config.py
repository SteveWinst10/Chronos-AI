from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env files."""

    PROJECT_NAME: str = "Chronos AI"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    VECTOR_DB_URL: str = "file:///backend/.data/vector"
    DATABASE_URL: str = "sqlite:///./chronos.db"

    OPENAI_API_KEY: Optional[str] = None
    LLM_API_KEY: Optional[str] = None
    NEWS_API_KEY: Optional[str] = None

    @property
    def NEO4J_USERNAME(self) -> str:
        return self.NEO4J_USER

    @property
    def effective_llm_api_key(self) -> Optional[str]:
        return self.OPENAI_API_KEY or self.LLM_API_KEY

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


settings = Settings()
