# Defines the generic form session database model.

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class FormSession(Base):
    __tablename__ = "form_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    client_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    scenario_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    answers_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
