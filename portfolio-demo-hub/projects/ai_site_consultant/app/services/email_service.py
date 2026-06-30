# Этот файл отправляет email через SMTP и сообщает о понятных ошибках настройки.

from email.message import EmailMessage
import smtplib
from typing import Protocol

from app.config import settings


class EmailSettings(Protocol):
    """Описывает SMTP-настройки, необходимые почтовому сервису."""
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_use_tls: bool
    email_from: str
    email_to: str


class EmailServiceError(RuntimeError):
    """Базовая ошибка SMTP-сервиса."""


class EmailConfigurationError(EmailServiceError):
    """Ошибка отсутствующих или противоречивых SMTP-настроек."""


class EmailDeliveryError(EmailServiceError):
    """Ошибка подключения, авторизации или отправки письма."""


class EmailService:
    """Отправляет текстовые письма через настроенный SMTP-сервер."""

    def __init__(self, email_settings: EmailSettings = settings) -> None:
        """Сохраняет SMTP-настройки сервиса."""
        self.settings = email_settings

    def send_email(self, subject: str, body: str) -> None:
        """Проверяет настройки и отправляет одно email-сообщение."""
        self._validate_settings()
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.settings.email_from
        message["To"] = self.settings.email_to
        message.set_content(body)

        try:
            with smtplib.SMTP(
                self.settings.smtp_host,
                self.settings.smtp_port,
                timeout=15,
            ) as smtp:
                if self.settings.smtp_use_tls:
                    smtp.starttls()
                if self.settings.smtp_user:
                    smtp.login(
                        self.settings.smtp_user,
                        self.settings.smtp_password,
                    )
                smtp.send_message(message)
        except smtplib.SMTPAuthenticationError as exc:
            raise EmailDeliveryError(
                "SMTP отклонил логин или пароль."
            ) from exc
        except (OSError, smtplib.SMTPException) as exc:
            raise EmailDeliveryError(
                "Не удалось подключиться к SMTP-серверу или отправить email."
            ) from exc

    def _validate_settings(self) -> None:
        """Выбрасывает понятную ошибку при неполной SMTP-конфигурации."""
        missing = [
            name
            for name, value in (
                ("SMTP_HOST", self.settings.smtp_host),
                ("SMTP_PORT", self.settings.smtp_port),
                ("EMAIL_FROM", self.settings.email_from),
                ("EMAIL_TO", self.settings.email_to),
            )
            if not value
        ]
        if missing:
            raise EmailConfigurationError(
                "Не заполнены SMTP-настройки: " + ", ".join(missing)
            )
        if self.settings.smtp_user and not self.settings.smtp_password:
            raise EmailConfigurationError(
                "SMTP_USER задан, но SMTP_PASSWORD отсутствует."
            )
        if self.settings.smtp_password and not self.settings.smtp_user:
            raise EmailConfigurationError(
                "SMTP_PASSWORD задан, но SMTP_USER отсутствует."
            )
        if not 1 <= self.settings.smtp_port <= 65535:
            raise EmailConfigurationError(
                "SMTP_PORT должен быть числом от 1 до 65535."
            )
        if "@" not in self.settings.email_from:
            raise EmailConfigurationError(
                "EMAIL_FROM должен содержать корректный email-адрес."
            )
        if "@" not in self.settings.email_to:
            raise EmailConfigurationError(
                "EMAIL_TO должен содержать корректный email-адрес."
            )
