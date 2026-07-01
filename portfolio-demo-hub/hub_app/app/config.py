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
    site_url: str = Field("http://localhost", alias="SITE_URL")
    contact_telegram: str = Field("your_telegram", alias="CONTACT_TELEGRAM")
    contact_email: str = Field("you@example.com", alias="CONTACT_EMAIL")
    contact_whatsapp: str = Field("972503213621", alias="CONTACT_WHATSAPP")
    contact_facebook: str = Field(
        "https://www.facebook.com/profile.php?id=61584187357263&locale=ru_RU",
        alias="CONTACT_FACEBOOK",
    )
    contact_photo_url: str = Field("/static/img/maxim-profile.jpg", alias="CONTACT_PHOTO_URL")
    projects_root: Path = Field(Path("/projects"), alias="PROJECTS_ROOT")
    demo_internal_base_url: str = Field("http://nginx", alias="DEMO_INTERNAL_BASE_URL")


@lru_cache
def get_settings() -> Settings:
    return Settings()
