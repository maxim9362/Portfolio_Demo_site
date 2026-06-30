# Этот файл содержит операции сохранения и чтения сообщений из базы данных.

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.message import Message


def save_message(
    db: Session,
    session_id: str,
    role: str,
    content: str,
) -> Message:
    """Сохраняет одно сообщение диалога в PostgreSQL."""
    message = Message(
        session_id=session_id,
        role=role,
        content=content,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_recent_messages(
    db: Session,
    session_id: str,
    limit: int = 6,
) -> list[Message]:
    """Загружает ограниченную последнюю часть истории по session_id."""
    if limit < 1:
        return []

    statement = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(limit)
    )
    messages = list(db.scalars(statement))
    messages.reverse()
    return messages


def get_all_messages(
    db: Session,
    session_id: str,
) -> list[Message]:
    """Загружает полную историю диалога в хронологическом порядке."""
    statement = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    )
    return list(db.scalars(statement))


def get_latest_messages(
    db: Session,
    session_id: str,
    limit: int = 12,
) -> list[Message]:
    """Возвращает последние сообщения сессии в хронологическом порядке."""
    return get_recent_messages(db, session_id, limit=limit)
