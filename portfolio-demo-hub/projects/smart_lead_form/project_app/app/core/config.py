# Loads application settings from environment variables.

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Smart Lead Form"
    app_env: str = "development"
    database_url: str = "postgresql://postgres:postgres@db:5432/smart_lead_form"
    default_client_id: str = "notary_demo"
    owner_email: str | None = "test@example.com"
    allowed_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    admin_api_key: str | None = None
    admin_username: str = "admin"
    admin_password: str = "admin123"
    public_base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


settings = Settings()
