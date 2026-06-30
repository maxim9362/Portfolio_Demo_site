# Builds and logs owner notification emails without sending real email.

import logging
from typing import Any

from app.core.config import settings
from app.services.form_engine import load_ui_texts


logger = logging.getLogger(__name__)


def _display_value(value: Any) -> str:
    """Return a readable fallback for empty values."""
    if value is None or value == "":
        return "-"
    return str(value)


def get_label(ui_texts: dict, group: str, value: str | None) -> str:
    """Return a human-readable label from UI texts, or a safe fallback."""
    if not value:
        return "-"

    labels = ui_texts.get("labels", {})
    group_labels = labels.get(group, {})

    return group_labels.get(value, value)


def format_price(lead) -> str:
    """Format the lead estimate as readable text."""
    currency = lead.currency or "₪"

    if lead.estimated_price_min is not None and lead.estimated_price_max is not None:
        return f"{lead.estimated_price_min}–{lead.estimated_price_max} {currency}"

    if lead.estimated_price_min is not None:
        return f"от {lead.estimated_price_min} {currency}"

    return "Стоимость нужно уточнить"


def build_owner_notification(lead) -> str:
    """Build the plain-text owner notification for a new lead."""
    ui_texts = load_ui_texts(lead.client_id)

    created_at = lead.created_at.isoformat() if lead.created_at else "-"

    return "\n".join(
        [
            "Новая заявка с сайта",
            "",
            f"Клиент: {_display_value(lead.client_id)}",
            f"Сценарий: {_display_value(lead.scenario_key)}",
            "",
            "Детали заявки:",
            f"Услуга: {get_label(ui_texts, 'service_type', lead.service_type)}",
            f"Язык: {get_label(ui_texts, 'language_pair', lead.language_pair)}",
            f"Страниц: {get_label(ui_texts, 'page_count', lead.page_count)}",
            f"Срочность: {get_label(ui_texts, 'urgency', lead.urgency)}",
            f"Формат связи: {get_label(ui_texts, 'meeting_format', lead.meeting_format)}",
            f"Город: {get_label(ui_texts, 'city', lead.city)}",
            f"Документы: {get_label(ui_texts, 'documents_ready', lead.documents_ready)}",
            "",
            "Контакты:",
            f"Имя: {_display_value(lead.name)}",
            f"Телефон: {_display_value(lead.phone)}",
            f"Email: {_display_value(lead.email)}",
            f"Удобное время: {_display_value(lead.preferred_contact_time)}",
            f"Комментарий: {_display_value(lead.comment)}",
            "",
            "Оценка:",
            format_price(lead),
            _display_value(lead.estimate_message),
            "",
            "Важно:",
            _display_value(lead.disclaimer),
            "",
            f"Дата создания: {created_at}",
        ]
    )


def notify_owner_about_new_lead(lead) -> None:
    """Log the owner notification that would be sent for a new lead."""
    if not settings.owner_email:
        logger.warning("Owner email is not configured; notification stub was not sent")
        return

    subject = "Новая заявка с сайта"
    body = build_owner_notification(lead)

    logger.info(
        "Owner notification email stub\nTo: %s\nSubject: %s\nBody:\n%s",
        settings.owner_email,
        subject,
        body,
    )
