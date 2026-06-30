# Initializes database tables and lightweight MVP schema updates.

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import Base, engine
from app.models import AdminUser, FormSession, Lead
from app.services.admin_auth_service import ensure_default_admin_user


def ensure_mvp_columns() -> None:
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'new'"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_leads_status ON leads (status)"))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_mvp_columns()
    with Session(engine) as db:
        ensure_default_admin_user(db)
