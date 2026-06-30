# Этот файл проверяет восстановление состояния диалога из базы после перезапуска backend.

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.repositories.lead_repository import (
    create_lead,
    create_lead_with_status,
    get_lead_by_session_id,
)
from app.repositories.message_repository import get_all_messages, save_message
from app.services.lead_state import build_lead_state
from app.services.session_service import get_or_create_session


class StatelessArchitectureTests(unittest.TestCase):
    """Проверяет хранение состояния вне памяти backend."""

    def test_concurrent_lead_insert_is_reported_as_existing(self) -> None:
        """Проверяет повторное конкурентное создание лида."""
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            get_or_create_session(db, "concurrent-lead")
            first = create_lead_with_status(
                db=db,
                session_id="concurrent-lead",
                name="Максим",
                phone="+972505767675",
                email=None,
                message="Ремонт кондиционера",
                preferred_contact_time="Завтра утром",
            )
            second = create_lead_with_status(
                db=db,
                session_id="concurrent-lead",
                name="Максим",
                phone="+972505767675",
                email=None,
                message="Ремонт кондиционера",
                preferred_contact_time="Завтра утром",
            )

            self.assertTrue(first.created)
            self.assertFalse(second.created)
            self.assertEqual(first.lead.id, second.lead.id)
        engine.dispose()

    def test_state_is_restored_by_a_new_database_session(self) -> None:
        """Проверяет восстановление контекста новым worker."""
        with TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "state.db"
            database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"

            first_engine = create_engine(database_url)
            Base.metadata.create_all(first_engine)
            with Session(first_engine) as first_worker:
                get_or_create_session(first_worker, "restart-session")
                messages = (
                    ("user", "Нужна чистка кондиционера"),
                    (
                        "assistant",
                        "Это плановая чистка или уже есть проблема?",
                    ),
                    ("user", "Слабый поток воздуха"),
                    ("assistant", "В каком городе нужен мастер?"),
                    ("user", "Ашдод"),
                    ("assistant", "Как к вам обращаться?"),
                    ("user", "Максим"),
                    (
                        "assistant",
                        "Оставьте номер телефона или email для связи.",
                    ),
                    ("user", "0505767675"),
                    (
                        "assistant",
                        "Когда вам удобно, чтобы менеджер связался?",
                    ),
                    ("user", "Завтра утром"),
                )
                for role, content in messages:
                    save_message(
                        first_worker,
                        "restart-session",
                        role,
                        content,
                    )

                create_lead(
                    db=first_worker,
                    session_id="restart-session",
                    name="Максим",
                    phone="+972505767675",
                    email=None,
                    message=(
                        "Услуга: чистка кондиционера. "
                        "Проблема: Слабый поток воздуха. "
                        "Город: Ашдод."
                    ),
                    preferred_contact_time="Завтра утром",
                )
            first_engine.dispose()

            second_engine = create_engine(database_url)
            with Session(second_engine) as second_worker:
                history = get_all_messages(
                    second_worker,
                    "restart-session",
                )
                lead = get_lead_by_session_id(
                    second_worker,
                    "restart-session",
                )
                state = build_lead_state(history, lead)

                self.assertEqual(len(history), len(messages))
                self.assertTrue(state.lead_created)
                self.assertEqual(state.service, "чистка кондиционера")
                self.assertEqual(state.problem, "Слабый поток воздуха")
                self.assertEqual(state.city, "Ашдод")
                self.assertEqual(state.name, "Максим")
                self.assertEqual(state.phone, "+972505767675")
                self.assertEqual(
                    state.preferred_contact_time,
                    "Завтра утром",
                )
            second_engine.dispose()


if __name__ == "__main__":
    unittest.main()
