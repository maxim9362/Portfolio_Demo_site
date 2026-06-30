# Этот файл загружает настройки приложения из переменных окружения и файла .env.

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Описывает настройки приложения из окружения и файла .env."""
    app_name: str = "Universal AI Site Consultant"
    debug: bool = False
    uvicorn_workers: int = Field(default=1, ge=1)
    admin_username: str = "admin"
    admin_password: str = "change_me"
    admin_session_secret: str = ""
    admin_cookie_secure: bool = False
    lead_retention_days: int = Field(default=14, ge=1)
    lead_cleanup_interval_seconds: int = Field(default=3600, ge=60)

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_consultant"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    gemini_fallback_model: str = "gemini-2.5-flash"
    embedding_model_name: str = (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    knowledge_dir: Path = PROJECT_ROOT / "knowledge"
    chroma_path: Path = PROJECT_ROOT / "chroma_data"
    chroma_collection: str = "business_knowledge"
    rag_max_distance: float = 0.78
    allowed_origins: str = (
        "http://localhost:8000,http://127.0.0.1:8000"
    )

    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    email_from: str = ""
    email_to: str = ""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("knowledge_dir", "chroma_path", mode="after")
    @classmethod
    def resolve_project_path(cls, value: Path) -> Path:
        """Преобразует относительный путь в путь от корня проекта."""
        if value.is_absolute():
            return value
        return PROJECT_ROOT / value

    @property
    def allowed_origin_list(self) -> list[str]:
        """Возвращает очищенный список разрешенных CORS-источников."""
        return [
            origin.strip().rstrip("/")
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]

    @model_validator(mode="after")
    def validate_admin_session_secret(self) -> "Settings":
        """Запрещает production-запуск без секрета административной сессии."""
        if not self.debug and not self.admin_session_secret.strip():
            raise ValueError(
                "ADMIN_SESSION_SECRET обязателен при DEBUG=false."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Создает и кэширует неизменяемую конфигурацию процесса."""
    return Settings()


settings = get_settings()
