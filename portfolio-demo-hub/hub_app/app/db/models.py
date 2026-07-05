"""Database tables owned by Portfolio Demo Hub.

The Hub stores public contact leads, visitor sessions, analytics events,
and wrapper-level demo sessions. Individual demo projects may have their own
separate databases and models.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ContactLead(Base):
    """A submitted contact form lead from the portfolio site."""

    __tablename__ = "contact_leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(80))
    email: Mapped[str | None] = mapped_column(String(255))
    client_type: Mapped[str | None] = mapped_column(String(120))
    interest: Mapped[str | None] = mapped_column(String(120))
    project_status: Mapped[str | None] = mapped_column(String(120))
    project_id: Mapped[str | None] = mapped_column(String(120), index=True)
    message: Mapped[str | None] = mapped_column(Text)
    source_page: Mapped[str | None] = mapped_column(String(500))
    session_id: Mapped[str | None] = mapped_column(String(120), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String(40), default="new", nullable=False)


class VisitorSession(Base):
    """One browser visitor tracked by the Hub analytics script."""

    __tablename__ = "visitor_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    ip_hash: Mapped[str | None] = mapped_column(String(128))
    user_agent: Mapped[str | None] = mapped_column(Text)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    bot_name: Mapped[str | None] = mapped_column(String(120))
    traffic_type: Mapped[str] = mapped_column(String(40), default="human", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnalyticsEvent(Base):
    """Append-only analytics event such as page views, clicks, and demo actions."""

    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(120), index=True)
    demo_session_id: Mapped[str | None] = mapped_column(String(120), index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(120), index=True)
    page_url: Mapped[str | None] = mapped_column(String(500))
    metadata_json: Mapped[str | None] = mapped_column(Text)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    bot_name: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DemoSession(Base):
    """A single launch of a demo project inside the Hub iframe wrapper."""

    __tablename__ = "demo_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    demo_session_id: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(120), index=True)
    project_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    opened_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    opened_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
