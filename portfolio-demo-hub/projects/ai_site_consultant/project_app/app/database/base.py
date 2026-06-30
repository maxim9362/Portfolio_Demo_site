# Этот файл объявляет базовый класс SQLAlchemy для всех моделей приложения.

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовый класс декларативных SQLAlchemy-моделей."""
