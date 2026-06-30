# Этот файл проверяет данные лида и создает одну заявку на пользовательскую сессию.

import re

from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.repositories.lead_repository import (
    append_lead_message,
    create_lead_with_status,
    get_lead_by_session_id,
    update_lead,
)
from app.services.lead_extractor import (
    extract_preferred_contact_time,
    extract_service,
    normalize_air_conditioner_text,
)
from app.services.notification_service import notify_new_lead
from app.services.working_hours import working_hours_notice


ADDITIONAL_DETAILS_PATTERN = (
    "не охлаждает",
    "не греет",
    "не включается",
    "не работает",
    "течет",
    "капает",
    "шумит",
    "вибрирует",
    "пахнет",
    "запах",
    "ошибка",
    "обмерз",
    "лед",
    "слабо дует",
)
ADDITION_INTENT_PATTERN = re.compile(
    r"\b(?:еще|ещё|также|добав\w*|кроме\s+того|и\s+еще|и\s+ещё)\b",
    re.IGNORECASE,
)


def create_or_update_lead(
    db: Session,
    session_id: str,
    name: str,
    phone: str | None,
    email: str | None,
    details: str | None,
    preferred_contact_time: str | None,
) -> Lead:
    """Создает новый лид или обновляет существующий по session_id."""
    existing_lead = get_lead_by_session_id(db, session_id)
    if existing_lead is not None:
        return update_lead(
            db=db,
            lead=existing_lead,
            name=name,
            phone=phone,
            email=email,
            message=details,
            preferred_contact_time=preferred_contact_time,
        )

    creation = create_lead_with_status(
        db=db,
        session_id=session_id,
        name=name,
        phone=phone,
        email=email,
        message=details,
        preferred_contact_time=preferred_contact_time,
    )
    if creation.created:
        notify_new_lead(creation.lead)
    return creation.lead


def add_details_to_existing_lead(
    db: Session,
    lead: Lead,
    user_message: str,
) -> str | None:
    """Обновляет время или добавляет новые детали к готовой заявке."""
    preferred_time = extract_preferred_contact_time(user_message)
    if preferred_time and preferred_time != lead.preferred_contact_time:
        lead = update_lead(
            db=db,
            lead=lead,
            name=lead.name,
            phone=lead.phone,
            email=lead.email,
            message=lead.message,
            preferred_contact_time=preferred_time,
        )
        response = (
            "Спасибо, обновил удобное время связи в вашей заявке: "
            f"{lead.preferred_contact_time}."
        )
        notice = working_hours_notice(lead.preferred_contact_time)
        return f"{response}\n{notice}" if notice else response

    normalized_message = normalize_air_conditioner_text(user_message)
    has_problem = any(
        marker in normalized_message
        for marker in ADDITIONAL_DETAILS_PATTERN
    )
    has_explicit_addition = bool(ADDITION_INTENT_PATTERN.search(user_message))
    has_new_service = extract_service(user_message) is not None
    if not has_problem and not (has_explicit_addition and has_new_service):
        return None

    append_lead_message(
        db=db,
        lead=lead,
        additional_details=user_message,
    )
    return "Спасибо. Добавил эту информацию к вашей заявке."


def format_lead_confirmation(lead: Lead) -> str:
    """Формирует итоговое подтверждение с данными заявки."""
    contact = lead.phone or lead.email or "не указан"
    detail_lines = [
        part.strip()
        for part in (lead.message or "").split(".")
        if part.strip()
    ]
    summary = [
        f"Спасибо, {lead.name or 'заявка принята'}.",
        "Заявка оформлена.",
        *detail_lines,
        f"Контакт: {contact}",
        (
            "Удобное время связи: "
            f"{lead.preferred_contact_time or 'не указано'}"
        ),
    ]
    notice = working_hours_notice(lead.preferred_contact_time)
    if notice:
        summary.append(notice)
    else:
        summary.append(
            "Менеджер свяжется с вами в указанное время или в ближайшее "
            "рабочее время."
        )
    return "\n".join(summary)
