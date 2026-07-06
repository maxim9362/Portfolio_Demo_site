"""Environment-driven settings for Portfolio Demo Hub.

Values come from `.env` in local development and from real environment
variables in Docker/production. Defaults match the development compose setup.
"""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """Typed application settings shared by routes, services, and startup code."""

    database_url: str = Field(
        "postgresql+psycopg://portfolio:portfolio@postgres:5432/portfolio",
        alias="DATABASE_URL",
    )
    admin_username: str = Field("admin", alias="ADMIN_USERNAME")
    admin_password: str = Field("change_me", alias="ADMIN_PASSWORD")
    admin_timezone: str = Field("Asia/Jerusalem", alias="ADMIN_TIMEZONE")
    app_env: str = Field("development", alias="APP_ENV")
    site_url: str = Field("http://localhost", alias="SITE_URL")
    contact_telegram: str = Field("your_telegram", alias="CONTACT_TELEGRAM")
    contact_email: str = Field("you@example.com", alias="CONTACT_EMAIL")
    contact_whatsapp: str = Field("972500000000", alias="CONTACT_WHATSAPP")
    contact_facebook: str = Field(
        "https://www.facebook.com/your-profile",
        alias="CONTACT_FACEBOOK",
    )
    contact_photo_url: str = Field("/static/img/maxim-profile.jpg", alias="CONTACT_PHOTO_URL")
    projects_root: Path = Field(Path("/projects"), alias="PROJECTS_ROOT")
    demo_internal_base_url: str = Field("http://nginx", alias="DEMO_INTERNAL_BASE_URL")


@lru_cache
def get_settings() -> Settings:
    """Return one cached Settings instance instead of reparsing env on every call."""
    return Settings()
