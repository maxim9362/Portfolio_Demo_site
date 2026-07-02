"""SQLAlchemy engine, declarative base, and request-scoped session dependency."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class used by all Hub database models."""

    pass


# `pool_pre_ping` keeps long-running Docker connections fresh after idle periods.
engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for FastAPI dependencies and close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
