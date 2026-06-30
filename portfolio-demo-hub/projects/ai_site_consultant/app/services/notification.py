# Этот файл сохраняет совместимые импорты старого сервиса уведомлений.

from app.models.lead import Lead
from app.services.notification_service import (
    format_lead_email,
    notify_new_lead,
)


def send_lead_notification(lead: Lead) -> bool:
    """Сохраняет совместимый интерфейс отправки уведомления о лиде."""
    return notify_new_lead(lead)
