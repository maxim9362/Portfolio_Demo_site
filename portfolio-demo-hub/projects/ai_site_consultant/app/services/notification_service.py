# Этот файл формирует уведомление о новом лиде и безопасно вызывает email-сервис.

import logging

from app.models.lead import Lead
from app.services.email_service import EmailService, EmailServiceError


logger = logging.getLogger(__name__)


def notify_new_lead(
    lead: Lead,
    email_service: EmailService | None = None,
) -> bool:
    """Отправляет владельцу email и не прерывает создание лида при ошибке."""
    service = email_service or EmailService()
    try:
        service.send_email(
            subject=f"Новая заявка #{lead.id}",
            body=format_lead_email(lead),
        )
    except EmailServiceError as exc:
        logger.error(
            "Email-уведомление для lead %s не отправлено: %s",
            lead.id,
            exc,
        )
        return False

    logger.info("Email-уведомление для lead %s отправлено", lead.id)
    return True


def format_lead_email(lead: Lead) -> str:
    """Формирует читаемый текст email с данными новой заявки."""
    contact = lead.phone or lead.email or "не указан"
    return "\n".join(
        (
            f"Заявка: #{lead.id}",
            f"Session ID: {lead.session_id}",
            f"Имя: {lead.name or 'не указано'}",
            f"Телефон: {lead.phone or 'не указан'}",
            f"Email: {lead.email or 'не указан'}",
            f"Контакт: {contact}",
            f"Удобное время: {lead.preferred_contact_time or 'не указано'}",
            f"Описание: {lead.message or 'не указано'}",
            f"Статус: {lead.status}",
        )
    )
