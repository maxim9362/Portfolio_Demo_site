# Этот файл проверяет авторизацию и основные действия административной панели.

import re
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.db import get_db
from app.main import app
from app.models.lead import Lead
from app.models.message import Message
from app.models.session import Session as ChatSession
from app.repositories.admin_repository import get_admin
from app.services.admin_service import ensure_initial_admin
from app.services.admin_security import verify_password


class AdminPanelTests(unittest.TestCase):
    """Проверяет вход, защиту маршрутов и управление заявками."""

    def setUp(self) -> None:
        """Создает общую in-memory базу и тестовый HTTP-клиент."""
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as db:
            ensure_initial_admin(db, "admin", "change_me")

        def override_get_db():
            """Открывает тестовую SQLAlchemy-сессию на один запрос."""
            with Session(self.engine) as db:
                yield db

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        """Закрывает клиент и удаляет dependency override."""
        self.client.close()
        app.dependency_overrides.clear()
        self.engine.dispose()

    def test_admin_redirects_to_login_without_session(self) -> None:
        """Проверяет защиту главной ссылки и списка заявок."""
        root = self.client.get("/admin", follow_redirects=False)
        leads = self.client.get("/admin/leads", follow_redirects=False)

        self.assertEqual(root.status_code, 303)
        self.assertEqual(root.headers["location"], "/admin/login")
        self.assertEqual(leads.status_code, 303)
        self.assertEqual(leads.headers["location"], "/admin/login")

    def test_invalid_and_valid_login(self) -> None:
        """Проверяет сообщение об ошибке и успешный вход."""
        csrf = self._csrf_from("/admin/login")
        invalid = self.client.post(
            "/admin/login",
            data={
                "csrf_token": csrf,
                "username": "admin",
                "password": "incorrect",
            },
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("Неверный логин или пароль", invalid.text)

        csrf = self._csrf_from("/admin/login")
        valid = self.client.post(
            "/admin/login",
            data={
                "csrf_token": csrf,
                "username": "admin",
                "password": "change_me",
            },
            follow_redirects=False,
        )
        self.assertEqual(valid.status_code, 303)
        self.assertEqual(valid.headers["location"], "/admin/leads")
        self.assertIn("ai_consultant_admin", self.client.cookies)
        self.assertIn("httponly", valid.headers["set-cookie"].casefold())

    def test_leads_detail_latest_status_and_delete(self) -> None:
        """Проверяет полный рабочий цикл заявки в админке."""
        self._login()
        lead_id = self._create_lead()

        page = self.client.get("/admin/leads")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Максим", page.text)
        self.assertIn("Ашдод", page.text)
        self.assertIn("ремонт кондиционера", page.text)

        detail = self.client.get(f"/admin/leads/{lead_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertIn("Не охлаждает", detail.text)
        self.assertIn("dialogue-admin-test", detail.text)
        self.assertIn('name="status"', detail.text)
        self.assertIn('value="new"', detail.text)

        latest = self.client.get("/admin/leads/latest-info")
        self.assertEqual(latest.status_code, 200)
        self.assertEqual(latest.json()["latest_lead_id"], lead_id)
        self.assertEqual(latest.json()["new_count"], 1)

        csrf = self._csrf_from(f"/admin/leads/{lead_id}")
        status = self.client.post(
            f"/admin/leads/{lead_id}/status",
            data={"csrf_token": csrf, "status": "in_progress"},
            follow_redirects=False,
        )
        self.assertEqual(status.status_code, 303)
        with Session(self.engine) as db:
            self.assertEqual(db.get(Lead, lead_id).status, "in_progress")

        csrf = self._csrf_from(f"/admin/leads/{lead_id}")
        deleted = self.client.post(
            f"/admin/leads/{lead_id}/delete",
            data={"csrf_token": csrf},
            follow_redirects=False,
        )
        self.assertEqual(deleted.status_code, 303)
        self.assertEqual(deleted.headers["location"], "/admin/leads")
        with Session(self.engine) as db:
            self.assertIsNone(db.get(Lead, lead_id))
            self.assertIsNone(db.get(ChatSession, 1))
            self.assertEqual(
                db.query(Message).filter_by(
                    session_id="dialogue-admin-test"
                ).count(),
                0,
            )

    def test_logout_requires_csrf_and_clears_session(self) -> None:
        """Проверяет защищенный выход из административной панели."""
        self._login()
        rejected = self.client.post(
            "/admin/logout",
            data={"csrf_token": "wrong"},
            follow_redirects=False,
        )
        self.assertEqual(rejected.status_code, 403)

        csrf = self._csrf_from("/admin/leads")
        response = self.client.post(
            "/admin/logout",
            data={"csrf_token": csrf},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        protected = self.client.get("/admin/leads", follow_redirects=False)
        self.assertEqual(protected.headers["location"], "/admin/login")

    def test_settings_change_username_and_password(self) -> None:
        """Проверяет смену доступа и обязательный повторный вход."""
        self._login()
        csrf = self._csrf_from("/admin/settings")
        changed = self.client.post(
            "/admin/settings",
            data={
                "csrf_token": csrf,
                "new_username": "owner",
                "current_password": "change_me",
                "new_password": "new_password_123",
                "new_password_confirm": "new_password_123",
            },
            follow_redirects=False,
        )
        self.assertEqual(changed.status_code, 303)
        self.assertEqual(changed.headers["location"], "/admin/login")

        with Session(self.engine) as db:
            admin = get_admin(db)
            self.assertEqual(admin.username, "owner")
            self.assertTrue(
                verify_password("new_password_123", admin.password_hash)
            )
            self.assertFalse(verify_password("change_me", admin.password_hash))

        csrf = self._csrf_from("/admin/login")
        relogin = self.client.post(
            "/admin/login",
            data={
                "csrf_token": csrf,
                "username": "owner",
                "password": "new_password_123",
            },
            follow_redirects=False,
        )
        self.assertEqual(relogin.status_code, 303)

    def test_post_actions_reject_invalid_csrf(self) -> None:
        """Проверяет CSRF-защиту изменения статуса и удаления."""
        self._login()
        lead_id = self._create_lead()
        response = self.client.post(
            f"/admin/leads/{lead_id}/status",
            data={"csrf_token": "invalid", "status": "done"},
        )
        self.assertEqual(response.status_code, 403)
        with Session(self.engine) as db:
            self.assertEqual(db.get(Lead, lead_id).status, "new")

    def test_admin_javascript_contains_notification_and_confirmation(self) -> None:
        """Проверяет polling, Notification API и подтверждение удаления."""
        source = self.client.get("/static/admin.js").text
        self.assertIn("Notification.requestPermission()", source)
        self.assertIn("/admin/leads/latest-info", source)
        self.assertIn("12000", source)
        self.assertIn("Удалить эту заявку?", source)
        self.assertNotIn("serviceWorker", source)
        self.assertNotIn("WebSocket", source)

    def _csrf_from(self, path: str) -> str:
        """Загружает страницу и извлекает CSRF-токен формы."""
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        match = re.search(
            r'name="csrf_token"\s+value="([^"]+)"',
            response.text,
        )
        self.assertIsNotNone(match)
        return match.group(1)

    def _login(self) -> None:
        """Выполняет вход стандартным тестовым администратором."""
        csrf = self._csrf_from("/admin/login")
        response = self.client.post(
            "/admin/login",
            data={
                "csrf_token": csrf,
                "username": "admin",
                "password": "change_me",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)

    def _create_lead(self) -> int:
        """Создает заявку и связанную сессию непосредственно в базе."""
        with Session(self.engine) as db:
            chat_session = ChatSession(session_id="dialogue-admin-test")
            db.add(chat_session)
            db.flush()
            lead = Lead(
                session_id=chat_session.session_id,
                name="Максим",
                phone="+972504334344",
                email="max@example.com",
                message=(
                    "Услуга: ремонт кондиционера. "
                    "Проблема: Не охлаждает. Город: Ашдод."
                ),
                preferred_contact_time="завтра утром",
                status="new",
            )
            db.add(lead)
            db.commit()
            db.refresh(lead)
            return lead.id


if __name__ == "__main__":
    unittest.main()
