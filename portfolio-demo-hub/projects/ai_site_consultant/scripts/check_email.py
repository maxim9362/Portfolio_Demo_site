# Этот файл вручную проверяет SMTP-настройки отправкой тестового email.

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.email_service import EmailService, EmailServiceError  # noqa: E402


def main() -> None:
    """Отправляет тестовое письмо с текущими SMTP-настройками."""
    try:
        EmailService().send_email(
            subject="Проверка email AI-консультанта",
            body=(
                "SMTP настроен правильно. Это тестовое письмо от "
                "Universal AI Site Consultant."
            ),
        )
    except EmailServiceError as exc:
        raise SystemExit(f"Ошибка проверки SMTP: {exc}") from exc

    print("Тестовый email успешно отправлен.")


if __name__ == "__main__":
    main()
