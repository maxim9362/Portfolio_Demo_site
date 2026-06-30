# Этот файл готовит модели заявок для отображения в HTML-админке.

from dataclasses import dataclass
from datetime import datetime
import re

from app.models.lead import Lead


STATUS_LABELS = {
    "new": "Новая",
    "in_progress": "В работе",
    "done": "Завершена",
    "cancelled": "Отменена",
}


@dataclass(frozen=True, slots=True)
class LeadView:
    """Содержит готовые для шаблона поля одной заявки."""

    id: int
    session_id: str
    name: str
    phone: str
    email: str
    city: str
    service: str
    problem: str
    message: str
    preferred_contact_time: str
    status: str
    status_label: str
    created_at: datetime
    created_at_text: str
    tel_href: str
    whatsapp_href: str


def present_lead(lead: Lead) -> LeadView:
    """Преобразует SQLAlchemy-модель заявки в представление шаблона."""
    message = (lead.message or "").strip()
    phone = (lead.phone or "").strip()
    return LeadView(
        id=lead.id,
        session_id=lead.session_id,
        name=lead.name or "Не указано",
        phone=phone or "Не указан",
        email=lead.email or "Не указан",
        city=_extract_detail(message, "Город") or "Не указан",
        service=_extract_detail(message, "Услуга") or "Не указана",
        problem=_extract_detail(message, "Проблема") or message or "Не указана",
        message=message or "Не указано",
        preferred_contact_time=lead.preferred_contact_time or "Не указано",
        status=lead.status,
        status_label=STATUS_LABELS.get(lead.status, lead.status),
        created_at=lead.created_at,
        created_at_text=lead.created_at.strftime("%d.%m.%Y %H:%M"),
        tel_href=f"tel:{phone}" if phone else "",
        whatsapp_href=_whatsapp_href(phone),
    )


def _extract_detail(message: str, label: str) -> str | None:
    """Извлекает подписанное поле из текстового описания заявки."""
    match = re.search(
        rf"(?:^|\n|[.!?]\s+){re.escape(label)}:\s*([^.\n]+)",
        message,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


def _whatsapp_href(phone: str) -> str:
    """Формирует международную ссылку WhatsApp из номера клиента."""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("0"):
        digits = f"972{digits[1:]}"
    if not digits:
        return ""
    return f"https://wa.me/{digits}"
