# Этот файл создает схему PostgreSQL и первую учетную запись администратора.

from sqlalchemy import inspect, text

import app.models  # noqa: F401
from app.config import settings
from app.database.base import Base
from app.database.db import SessionLocal, engine
from app.models.admin_credential import AdminCredential
from app.models.lead import Lead
from app.services.admin_service import ensure_initial_admin


def initialize_database() -> AdminCredential:
    """Идемпотентно подготавливает общую базу чата и админки."""
    Base.metadata.create_all(bind=engine)
    columns = {
        column["name"]
        for column in inspect(engine).get_columns("leads")
    }
    if "preferred_contact_time" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE leads ADD COLUMN "
                    "preferred_contact_time VARCHAR(255)"
                )
            )

    lead_session_index = next(
        index
        for index in Lead.__table__.indexes
        if index.name == "uq_leads_session_id"
    )
    lead_session_index.create(bind=engine, checkfirst=True)

    with SessionLocal() as db:
        return ensure_initial_admin(
            db=db,
            username=settings.admin_username,
            password=settings.admin_password,
        )
