from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    database_url: str = Field(
        "postgresql+psycopg://portfolio:portfolio@postgres:5432/portfolio",
        alias="DATABASE_URL",
    )
    admin_username: str = Field("admin", alias="ADMIN_USERNAME")
    admin_password: str = Field("change_me", alias="ADMIN_PASSWORD")
    app_env: str = Field("development", alias="APP_ENV")
    projects_root: Path = Field(Path("/projects"), alias="PROJECTS_ROOT")
    demo_internal_base_url: str = Field("http://nginx", alias="DEMO_INTERNAL_BASE_URL")


@lru_cache
def get_settings() -> Settings:
    return Settings()
