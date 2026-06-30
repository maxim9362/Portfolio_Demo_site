# Этот файл проверяет endpoint, CORS и автономность WordPress chat widget.

from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from app.main import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WIDGET_FILE = PROJECT_ROOT / "app" / "widget" / "chat-widget.js"


class WidgetTests(unittest.TestCase):
    """Проверяет выдачу виджета и CORS-поведение."""

    @classmethod
    def setUpClass(cls) -> None:
        """Создает тестовый HTTP-клиент FastAPI."""
        cls.client = TestClient(app)

    def test_widget_endpoint_returns_javascript(self) -> None:
        """Проверяет MIME-тип и содержимое скрипта."""
        response = self.client.get("/widget/chat-widget.js")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response.headers["content-type"].startswith(
                "application/javascript"
            )
        )
        self.assertIn(
            "initializeUniversalAiSiteConsultantWidget",
            response.text,
        )

    def test_cors_allows_configured_local_origin(self) -> None:
        """Проверяет разрешение настроенного источника."""
        response = self.client.options(
            "/api/chat",
            headers={
                "Origin": "http://localhost:8000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "http://localhost:8000",
        )

    def test_cors_does_not_allow_unknown_origin(self) -> None:
        """Проверяет блокировку неизвестного источника."""
        response = self.client.options(
            "/api/chat",
            headers={
                "Origin": "https://unknown.example",
                "Access-Control-Request-Method": "POST",
            },
        )

        self.assertNotIn(
            "access-control-allow-origin",
            response.headers,
        )

    def test_widget_has_no_external_frontend_dependencies(self) -> None:
        """Проверяет автономность JavaScript-виджета."""
        source = WIDGET_FILE.read_text(encoding="utf-8")

        self.assertIn("(function", source)
        self.assertIn("uaisc-", source)
        self.assertIn("localStorage", source)
        self.assertIn("response.body.getReader()", source)
        self.assertNotIn("jQuery", source)
        self.assertNotIn("<iframe", source.casefold())
        self.assertNotIn("cdn.", source.casefold())


if __name__ == "__main__":
    unittest.main()
