# Этот файл проверяет автоматическое удаление заявок после срока хранения.

from datetime import datetime, timedelta, timezone
import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.lead import Lead
from app.models.message import Message
from app.models.session import Session as ChatSession
from app.repositories.lead_repository import delete_leads_created_before


class DataRetentionTests(unittest.TestCase):
    """Проверяет полное удаление старых заявок и сохранение свежих."""

    def setUp(self) -> None:
        """Создает изолированную базу с двумя заявками."""
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        now = datetime.now(timezone.utc)

        with Session(self.engine) as db:
            for session_id, created_at in (
                ("old-dialogue", now - timedelta(days=15)),
                ("fresh-dialogue", now - timedelta(days=13)),
            ):
                db.add(
                    ChatSession(
                        session_id=session_id,
                        created_at=created_at,
                        updated_at=created_at,
                    )
                )
                db.add(
                    Message(
                        session_id=session_id,
                        role="user",
                        content="Тест",
                        created_at=created_at,
                    )
                )
                db.add(
                    Lead(
                        session_id=session_id,
                        name="Клиент",
                        phone="+972501234567",
                        status="new",
                        created_at=created_at,
                    )
                )
            db.commit()

    def tearDown(self) -> None:
        """Удаляет тестовую базу."""
        self.engine.dispose()

    def test_cleanup_removes_only_expired_lead_and_dialogue(self) -> None:
        """Проверяет границу хранения в 14 суток."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=14)

        with Session(self.engine) as db:
            deleted_count = delete_leads_created_before(db, cutoff)

        with Session(self.engine) as db:
            remaining_sessions = list(
                db.scalars(select(ChatSession.session_id))
            )
            remaining_messages = list(
                db.scalars(select(Message.session_id))
            )
            remaining_leads = list(db.scalars(select(Lead.session_id)))

        self.assertEqual(deleted_count, 1)
        self.assertEqual(remaining_sessions, ["fresh-dialogue"])
        self.assertEqual(remaining_messages, ["fresh-dialogue"])
        self.assertEqual(remaining_leads, ["fresh-dialogue"])


if __name__ == "__main__":
    unittest.main()
