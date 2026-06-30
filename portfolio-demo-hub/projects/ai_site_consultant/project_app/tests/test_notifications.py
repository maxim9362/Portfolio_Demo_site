# Этот файл проверяет SMTP-отправку и безопасные уведомления о новых лидах.

from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.lead import Lead
from app.models.session import Session as ChatSession
from app.services.email_service import (
    EmailConfigurationError,
    EmailService,
)
from app.services.lead_service import create_or_update_lead
from app.services.notification_service import (
    format_lead_email,
    notify_new_lead,
)


def make_email_settings(**overrides: object) -> SimpleNamespace:
    """Создает SMTP-настройки для тестов."""
    values = {
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "smtp_user": "mailer",
        "smtp_password": "secret",
        "smtp_use_tls": True,
        "email_from": "site@example.com",
        "email_to": "owner@example.com",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def make_lead() -> Lead:
    """Создает модель лида для проверки уведомлений."""
    return Lead(
        id=12,
        session_id="notification-test",
        name="Максим",
        phone="+972501234567",
        email=None,
        message=(
            "Услуга: ремонт кондиционера. "
            "Проблема: течет вода. Город: Ашдод."
        ),
        preferred_contact_time="завтра утром",
        status="new",
    )


class EmailServiceTests(unittest.TestCase):
    """Проверяет валидацию и отправку SMTP-писем."""

    @patch("app.services.email_service.smtplib.SMTP")
    def test_email_service_sends_message_through_smtp(
        self,
        smtp_class: MagicMock,
    ) -> None:
        """Проверяет успешную отправку письма через SMTP."""
        smtp = smtp_class.return_value.__enter__.return_value
        service = EmailService(make_email_settings())

        service.send_email("Новая заявка", "Текст заявки")

        smtp_class.assert_called_once_with(
            "smtp.example.com",
            587,
            timeout=15,
        )
        smtp.starttls.assert_called_once_with()
        smtp.login.assert_called_once_with("mailer", "secret")
        smtp.send_message.assert_called_once()

    def test_missing_smtp_settings_raise_clear_error(self) -> None:
        """Проверяет ошибку при пустых SMTP-настройках."""
        service = EmailService(
            make_email_settings(
                smtp_host="",
                email_from="",
                email_to="",
            )
        )

        with self.assertRaisesRegex(
            EmailConfigurationError,
            "SMTP_HOST, EMAIL_FROM, EMAIL_TO",
        ):
            service.send_email("Новая заявка", "Текст заявки")

    def test_invalid_smtp_port_raises_clear_error(self) -> None:
        """Проверяет отклонение недопустимого SMTP-порта."""
        service = EmailService(make_email_settings(smtp_port=70000))

        with self.assertRaisesRegex(
            EmailConfigurationError,
            "SMTP_PORT",
        ):
            service.send_email("Новая заявка", "Текст заявки")


class NotificationTests(unittest.TestCase):
    """Проверяет формат и правила уведомлений о лидах."""

    def test_notification_error_is_logged_without_crashing(self) -> None:
        """Проверяет, что SMTP-ошибка не ломает создание заявки."""
        service = MagicMock(spec=EmailService)
        service.send_email.side_effect = EmailConfigurationError(
            "Не заполнены SMTP-настройки: EMAIL_TO"
        )

        with self.assertLogs(
            "app.services.notification_service",
            level="ERROR",
        ) as captured:
            result = notify_new_lead(make_lead(), service)

        self.assertFalse(result)
        self.assertIn("не отправлено", captured.output[0])
        self.assertIn("EMAIL_TO", captured.output[0])

    def test_email_contains_contact_time_and_request_details(self) -> None:
        """Проверяет важные поля в тексте письма."""
        content = format_lead_email(make_lead())

        self.assertIn("Имя: Максим", content)
        self.assertIn("Контакт: +972501234567", content)
        self.assertIn("Удобное время: завтра утром", content)
        self.assertIn("Проблема: течет вода", content)

    def test_lead_service_notifies_only_after_new_lead_creation(self) -> None:
        """Проверяет единственное уведомление при создании лида."""
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)
        db.add(ChatSession(session_id="lead-email-test"))
        db.commit()

        try:
            with patch(
                "app.services.lead_service.notify_new_lead"
            ) as notify:
                first_lead = create_or_update_lead(
                    db=db,
                    session_id="lead-email-test",
                    name="Максим",
                    phone="+972501234567",
                    email=None,
                    details="Ремонт кондиционера в Ашдоде.",
                    preferred_contact_time="завтра утром",
                )
                updated_lead = create_or_update_lead(
                    db=db,
                    session_id="lead-email-test",
                    name="Максим",
                    phone="+972501234567",
                    email=None,
                    details="Добавлена информация о шуме.",
                    preferred_contact_time="завтра утром",
                )

            notify.assert_called_once_with(first_lead)
            self.assertEqual(first_lead.id, updated_lead.id)
        finally:
            db.close()
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
