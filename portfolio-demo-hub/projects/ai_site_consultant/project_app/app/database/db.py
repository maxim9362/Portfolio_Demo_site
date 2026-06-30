# Этот файл настраивает подключение к базе данных и dependency для FastAPI.

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


database_url = make_url(settings.database_url)
connect_args = (
    {"connect_timeout": 5}
    if database_url.get_backend_name() == "postgresql"
    else {}
)

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Открывает SQLAlchemy-сессию на время одного запроса."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
