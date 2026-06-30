# Этот файл содержит бизнес-логику получения или создания сессии чата.

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DatabaseSession

from app.models.session import Session


def get_or_create_session(
    db: DatabaseSession,
    session_id: str,
) -> Session:
    """Находит или безопасно создает сессию при конкурентных запросах."""
    normalized_session_id = session_id.strip()
    if not normalized_session_id:
        raise ValueError("session_id не может быть пустым")

    existing_session = db.scalar(
        select(Session).where(Session.session_id == normalized_session_id)
    )
    if existing_session is not None:
        return existing_session

    chat_session = Session(session_id=normalized_session_id)
    db.add(chat_session)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        concurrent_session = db.scalar(
            select(Session).where(Session.session_id == normalized_session_id)
        )
        if concurrent_session is None:
            raise
        return concurrent_session

    db.refresh(chat_session)
    return chat_session
