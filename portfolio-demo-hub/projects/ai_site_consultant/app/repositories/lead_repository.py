# Этот файл содержит операции создания и чтения лидов из базы данных.

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.message import Message
from app.models.session import Session as ChatSession


@dataclass(frozen=True, slots=True)
class LeadCreationResult:
    """Сообщает, был ли лид создан или найден после конфликта."""
    lead: Lead
    created: bool


def get_lead_by_session_id(
    db: Session,
    session_id: str,
) -> Lead | None:
    """Находит единственный лид по идентификатору диалога."""
    return db.scalar(
        select(Lead).where(Lead.session_id == session_id)
    )


def create_lead(
    db: Session,
    session_id: str,
    name: str,
    phone: str | None,
    email: str | None,
    message: str | None,
    preferred_contact_time: str | None = None,
) -> Lead:
    """Создает лид и возвращает сохраненную модель."""
    return create_lead_with_status(
        db=db,
        session_id=session_id,
        name=name,
        phone=phone,
        email=email,
        message=message,
        preferred_contact_time=preferred_contact_time,
    ).lead


def create_lead_with_status(
    db: Session,
    session_id: str,
    name: str,
    phone: str | None,
    email: str | None,
    message: str | None,
    preferred_contact_time: str | None = None,
) -> LeadCreationResult:
    """Атомарно создает лид с учетом параллельных запросов."""
    lead = Lead(
        session_id=session_id,
        name=name,
        phone=phone,
        email=email,
        message=message,
        preferred_contact_time=preferred_contact_time,
        status="new",
    )
    db.add(lead)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_lead = get_lead_by_session_id(db, session_id)
        if existing_lead is None:
            raise
        return LeadCreationResult(lead=existing_lead, created=False)

    db.refresh(lead)
    return LeadCreationResult(lead=lead, created=True)


def update_lead(
    db: Session,
    lead: Lead,
    name: str,
    phone: str | None,
    email: str | None,
    message: str | None,
    preferred_contact_time: str | None = None,
) -> Lead:
    """Обновляет контактные данные и описание существующего лида."""
    lead.name = name
    lead.phone = phone
    lead.email = email
    lead.message = message
    lead.preferred_contact_time = preferred_contact_time
    db.commit()
    db.refresh(lead)
    return lead


def append_lead_message(
    db: Session,
    lead: Lead,
    additional_details: str,
) -> Lead:
    """Добавляет новую уникальную заметку к существующей заявке."""
    normalized_details = additional_details.strip()
    if not normalized_details:
        return lead

    existing_message = (lead.message or "").strip()
    if normalized_details.casefold() in existing_message.casefold():
        return lead

    lead.message = (
        f"{existing_message}\nДополнение: {normalized_details}"
        if existing_message
        else f"Дополнение: {normalized_details}"
    )
    db.commit()
    db.refresh(lead)
    return lead


def list_leads(db: Session) -> list[Lead]:
    """Возвращает все заявки от новых к старым."""
    statement = select(Lead).order_by(
        Lead.created_at.desc(),
        Lead.id.desc(),
    )
    return list(db.scalars(statement))


def get_lead_by_id(db: Session, lead_id: int) -> Lead | None:
    """Находит заявку по ее числовому идентификатору."""
    return db.get(Lead, lead_id)


def update_lead_status(
    db: Session,
    lead: Lead,
    status: str,
) -> Lead:
    """Сохраняет новый статус заявки."""
    lead.status = status
    db.commit()
    db.refresh(lead)
    return lead


def delete_lead(db: Session, lead: Lead) -> None:
    """Полностью удаляет заявку, ее сообщения и сессию из базы."""
    session_id = lead.session_id
    db.execute(
        sql_delete(Message).where(Message.session_id == session_id)
    )
    db.execute(
        sql_delete(Lead).where(Lead.session_id == session_id)
    )
    db.execute(
        sql_delete(ChatSession).where(
            ChatSession.session_id == session_id
        )
    )
    db.commit()


def delete_leads_created_before(
    db: Session,
    cutoff: datetime,
) -> int:
    """Удаляет заявки старше cutoff вместе с диалогами и сессиями."""
    session_ids = list(
        db.scalars(
            select(Lead.session_id).where(Lead.created_at < cutoff)
        )
    )
    if not session_ids:
        return 0

    db.execute(
        sql_delete(Message).where(Message.session_id.in_(session_ids))
    )
    db.execute(
        sql_delete(Lead).where(Lead.session_id.in_(session_ids))
    )
    db.execute(
        sql_delete(ChatSession).where(
            ChatSession.session_id.in_(session_ids)
        )
    )
    db.commit()
    return len(session_ids)


def get_latest_lead(db: Session) -> Lead | None:
    """Возвращает последнюю созданную заявку."""
    statement = select(Lead).order_by(
        Lead.created_at.desc(),
        Lead.id.desc(),
    ).limit(1)
    return db.scalar(statement)


def count_new_leads(db: Session) -> int:
    """Считает заявки со статусом new."""
    statement = select(func.count(Lead.id)).where(Lead.status == "new")
    return int(db.scalar(statement) or 0)
