# Этот файл проверяет пять реальных сценариев консультации и оформления заявок.

import asyncio
from datetime import datetime
import unittest
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models import Lead
from app.repositories.lead_repository import get_lead_by_session_id
from app.services.chat_service import stream_chat_answer
from app.services.lead_dialogue import (
    ASK_CITY,
    ASK_CONTACT,
    ASK_CONTACT_TIME,
    ASK_NAME,
    ASK_PROBLEM,
    BOOKING_DECLINED,
    CLARIFY_CONTACT,
    CLARIFY_CITY,
    CLARIFY_INCOMPLETE_CONTACT_TIME,
    PROVISIONAL_AREA_OFFER,
)
from app.services.lead_extractor import (
    extract_problem,
    extract_phone,
    extract_preferred_contact_time,
    is_incomplete_contact_time,
)
from app.services.lead_service import add_details_to_existing_lead
from app.services.working_hours import (
    is_company_open,
    preferred_time_is_outside_hours,
    working_hours_notice,
)


class ConversationLogicTests(unittest.TestCase):
    """Проверяет консультацию и оформление заявок."""

    def setUp(self) -> None:
        """Создает изолированную базу для теста."""
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def tearDown(self) -> None:
        """Закрывает тестовую сессию базы."""
        self.db.close()
        self.engine.dispose()

    def test_dialogue_1_repair_leak_creates_complete_lead(self) -> None:
        """Проверяет оформление ремонта при течи."""
        session_id = "dialogue-repair"
        self.assertEqual(
            self._chat(
                session_id,
                "Хочу оформить заявку на ремонт кондеционера",
            ),
            ASK_PROBLEM,
        )
        helpful_answer = self._chat(session_id, "Из него течет вода")
        self.assertIn("250–450 ₪", helpful_answer)
        self.assertNotIn("телефон", helpful_answer.casefold())

        self.assertEqual(self._chat(session_id, "Ашдод"), ASK_NAME)
        self.assertEqual(self._chat(session_id, "Максим"), ASK_CONTACT)
        self.assertEqual(
            self._chat(session_id, "0501234567"),
            ASK_CONTACT_TIME,
        )

        confirmation = self._chat(session_id, "Завтра утром")
        self.assertIn("Заявка оформлена.", confirmation)
        self.assertIn("Город: Ашдод", confirmation)
        self.assertIn("Удобное время связи: Завтра утром", confirmation)

        lead = get_lead_by_session_id(self.db, session_id)
        self.assertEqual(lead.name, "Максим")
        self.assertEqual(lead.phone, "+972501234567")
        self.assertEqual(lead.preferred_contact_time, "Завтра утром")
        self.assertEqual(self._chat(session_id, "спасибо"), "")
        self.assertEqual(self._chat(session_id, "ок"), "")
        self.assertEqual(self._chat(session_id, "до свидания"), "")

    def test_dialogue_2_invalid_phone_is_requested_again(self) -> None:
        """Проверяет повторный запрос неверного телефона."""
        session_id = "dialogue-invalid-phone"
        self._reach_contact_step(session_id)

        self.assertEqual(
            self._chat(session_id, "504433223"),
            CLARIFY_CONTACT,
        )
        self.assertIsNone(get_lead_by_session_id(self.db, session_id))
        self.assertEqual(
            self._chat(session_id, "+972541234567"),
            ASK_CONTACT_TIME,
        )
        confirmation = self._chat(session_id, "Сегодня вечером")
        self.assertIn("Заявка оформлена.", confirmation)
        lead = get_lead_by_session_id(self.db, session_id)
        self.assertEqual(lead.phone, "+972541234567")
        self.assertEqual(lead.preferred_contact_time, "Сегодня вечером")

    def test_unlisted_city_can_be_submitted_for_area_confirmation(self) -> None:
        """Проверяет заявку для города вне основного списка."""
        session_id = "out-of-area-city"

        self._chat(session_id, "Привет. У меня сломался кондиционер")
        diagnostic_answer = self._chat(session_id, "Шумит")
        area_answer = self._chat(session_id, "Нетания")

        self.assertIn("Шум часто связан", diagnostic_answer)
        self.assertIn("Нетания не входит в основной список", area_answer)
        self.assertIn("может находиться в зоне", area_answer)
        self.assertIn("Хотите, я оформлю заявку", area_answer)
        self.assertNotIn("Шум часто связан", area_answer)
        self.assertIsNone(get_lead_by_session_id(self.db, session_id))

        self.assertEqual(self._chat(session_id, "да"), ASK_NAME)
        self.assertEqual(self._chat(session_id, "Максим"), ASK_CONTACT)
        self.assertEqual(
            self._chat(session_id, "0501234567"),
            ASK_CONTACT_TIME,
        )
        confirmation = self._chat(session_id, "завтра утром")
        lead = get_lead_by_session_id(self.db, session_id)

        self.assertIn("Заявка оформлена.", confirmation)
        self.assertIn("Город: Нетания", lead.message)
        self.assertIn("требует подтверждения менеджером", lead.message)

    def test_unknown_city_gets_short_city_clarification(self) -> None:
        """Проверяет короткое уточнение после нераспознанного города."""
        session_id = "unknown-city"

        self._chat(session_id, "У меня сломался кондиционер")
        self._chat(session_id, "Шумит")

        self.assertEqual(self._chat(session_id, "не знаю"), CLARIFY_CITY)

    def test_planned_cleaning_moves_to_city(self) -> None:
        """Проверяет распознавание плановой чистки без симптомов."""
        session_id = "planned-cleaning"

        self._chat(
            session_id,
            "Хочу оформить заявку на чистку кондиционера",
        )

        self.assertEqual(self._chat(session_id, "Плановая чистка"), ASK_CITY)
        self.assertEqual(self._chat(session_id, "Явне"), ASK_NAME)

    def test_unlisted_city_requires_confirmation_before_name(self) -> None:
        """Проверяет подтверждение зоны даже при явном вызове мастера."""
        session_id = "explicit-unlisted-city"

        self._chat(
            session_id,
            "Хочу вызвать мастера, кондиционер шумит",
        )
        response = self._chat(session_id, "поселок Эзер")

        self.assertEqual(
            response,
            PROVISIONAL_AREA_OFFER.format(city="Поселок Эзер"),
        )
        self.assertEqual(self._chat(session_id, "да"), ASK_NAME)
        self.assertEqual(self._chat(session_id, "Даниил"), ASK_CONTACT)

    def test_problem_extractor_returns_only_symptom(self) -> None:
        """Проверяет краткое описание проблемы для админки."""
        self.assertEqual(
            extract_problem(
                "Привет, кондиционер не охлаждает, город Ашдод"
            ),
            "не охлаждает",
        )
        self.assertEqual(
            extract_problem(
                "Хочу оформить заявку: кондиционер течет, телефон 0501234567"
            ),
            "течет",
        )

    def test_dialogue_3_installation_accepts_email_contact(self) -> None:
        """Проверяет заявку с email вместо телефона."""
        session_id = "dialogue-installation"
        first_answer = self._chat(
            session_id,
            "Хочу оформить заявку на установку кондиционера",
        )
        self.assertEqual(first_answer, ASK_CITY)
        self.assertEqual(
            self._chat(session_id, "Явне"),
            ASK_NAME,
        )
        self.assertEqual(self._chat(session_id, "Анна"), ASK_CONTACT)
        self.assertEqual(
            self._chat(session_id, "anna@example.com"),
            ASK_CONTACT_TIME,
        )
        confirmation = self._chat(session_id, "В любое время")

        lead = get_lead_by_session_id(self.db, session_id)
        self.assertIn("Заявка оформлена.", confirmation)
        self.assertEqual(lead.email, "anna@example.com")
        self.assertEqual(lead.preferred_contact_time, "В любое время")
        self.assertIn("установка кондиционера", lead.message)

    def test_dialogue_4_existing_lead_receives_additional_details(self) -> None:
        """Проверяет дополнение существующей заявки."""
        session_id = "dialogue-addition"
        self._create_repair_lead(session_id)

        response = self._chat(
            session_id,
            "Еще кондиционер шумит и вибрирует",
        )
        self.assertEqual(
            response,
            "Спасибо. Добавил эту информацию к вашей заявке.",
        )
        lead = get_lead_by_session_id(self.db, session_id)
        self.assertIn("Еще кондиционер шумит и вибрирует", lead.message)
        self.assertEqual(
            self.db.query(Lead).filter_by(session_id=session_id).count(),
            1,
        )
        status_response = self._chat(session_id, "Какой статус заявки?")
        self.assertIn("ожидает обработки менеджером", status_response)
        self.assertNotIn("телефон", status_response.casefold())
        time_response = self._chat(session_id, "сегодня в 23:00")
        self.assertIn("сегодня в 23:00", time_response)
        self.assertIn("компания обычно не работает", time_response)
        self.assertIn("воскресенье–четверг 09:00–18:00", time_response)
        self.assertIn("пятница 09:00–13:00", time_response)
        self.assertIn("суббота — выходной", time_response)
        lead = get_lead_by_session_id(self.db, session_id)
        self.assertEqual(lead.preferred_contact_time, "сегодня в 23:00")
        self.assertIsNone(
            self._chat_with_update_check(
                session_id,
                "Сколько стоит ремонт?",
            )
        )

    def test_dialogue_5_working_hours_and_phone_rules(self) -> None:
        """Проверяет телефоны и рабочие часы."""
        self.assertEqual(extract_phone("0501234567"), "+972501234567")
        self.assertEqual(extract_phone("0521234567"), "+972521234567")
        self.assertEqual(extract_phone("+972581234567"), "+972581234567")
        self.assertIsNone(extract_phone("504433223"))
        self.assertIsNone(extract_phone("123"))
        self.assertIsNone(extract_phone("999999"))

        timezone = ZoneInfo("Asia/Jerusalem")
        sunday_morning = datetime(2026, 6, 21, 10, 0, tzinfo=timezone)
        saturday_morning = datetime(2026, 6, 20, 10, 0, tzinfo=timezone)
        self.assertTrue(is_company_open(sunday_morning))
        self.assertFalse(is_company_open(saturday_morning))
        self.assertTrue(preferred_time_is_outside_hours("завтра после 20:00"))
        self.assertTrue(
            preferred_time_is_outside_hours("в пятницу после 15:00")
        )
        friday_morning = datetime(2026, 6, 19, 10, 0, tzinfo=timezone)
        self.assertTrue(
            preferred_time_is_outside_hours(
                "завтра в 10:00",
                friday_morning,
            )
        )
        self.assertIn(
            "ближайшее доступное рабочее время",
            working_hours_notice(
                "завтра после 20:00",
                sunday_morning,
            ),
        )
        self.assertIn(
            "воскресенье–четверг 09:00–18:00",
            working_hours_notice(
                "завтра после 20:00",
                sunday_morning,
            ),
        )

        session_id = "dialogue-outside-hours"
        first_answer = self._chat(
            session_id,
            "Хочу оформить заявку на чистку кондиционера",
        )
        self.assertIn("плановая чистка", first_answer)
        booking_answer = self._chat(
            session_id,
            "Слабый поток воздуха",
        )
        self.assertEqual(booking_answer, ASK_CITY)
        self._chat(session_id, "Кирьят-Малахи")
        self._chat(session_id, "Олег")
        self._chat(session_id, "0581234567")
        confirmation = self._chat(
            session_id,
            "В пятницу после 15:00",
        )
        self.assertIn("Заявка оформлена.", confirmation)
        self.assertIn(
            "ближайшее доступное рабочее время",
            confirmation,
        )
        lead = get_lead_by_session_id(self.db, session_id)
        self.assertEqual(
            lead.preferred_contact_time,
            "В пятницу после 15:00",
        )

    def test_contact_time_formats_from_pdf(self) -> None:
        """Проверяет разговорные форматы времени."""
        timezone = ZoneInfo("Asia/Jerusalem")
        noon = datetime(2026, 6, 21, 12, 0, tzinfo=timezone)
        afternoon = datetime(2026, 6, 21, 16, 0, tzinfo=timezone)

        expected = {
            "13:44": "сегодня в 13:44",
            "9:00": "завтра в 09:00",
            "09:30": "завтра в 09:30",
            "13.30": "сегодня в 13:30",
            "9-05": "завтра в 09:05",
            "в 15:00": "в 15:00",
            "после 17:00": "после 17:00",
            "до 16:00": "до 16:00",
            "с 10 до 12": "с 10 до 12",
            "с 10:00 до 12:00": "с 10:00 до 12:00",
            "после обеда": "после обеда",
            "утром": "утром",
            "вечером": "вечером",
            "завтра утром": "завтра утром",
            "завтра после 17:00": "завтра после 17:00",
            "12:55 сегодня": "сегодня в 12:55",
            "сегодня 12:55": "сегодня в 12:55",
            "9.05 завтра": "завтра в 09:05",
            "в любое время": "в любое время",
        }
        for source, result in expected.items():
            with self.subTest(source=source):
                self.assertEqual(
                    extract_preferred_contact_time(source, noon),
                    result,
                )

        self.assertEqual(
            extract_preferred_contact_time("13:44", afternoon),
            "завтра в 13:44",
        )
        self.assertTrue(is_incomplete_contact_time("13:3"))
        self.assertIsNone(extract_preferred_contact_time("13:3", noon))

    def test_incomplete_then_numeric_time_creates_lead(self) -> None:
        """Проверяет уточнение неполного времени."""
        session_id = "dialogue-numeric-time"
        self._reach_contact_step(session_id)
        self.assertEqual(
            self._chat(session_id, "0501234567"),
            ASK_CONTACT_TIME,
        )
        self.assertEqual(
            self._chat(session_id, "13:3"),
            CLARIFY_INCOMPLETE_CONTACT_TIME,
        )
        self.assertIsNone(get_lead_by_session_id(self.db, session_id))

        confirmation = self._chat(session_id, "13:44")
        lead = get_lead_by_session_id(self.db, session_id)
        self.assertIn("Заявка оформлена.", confirmation)
        self.assertRegex(
            lead.preferred_contact_time,
            r"^(?:сегодня|завтра) в 13:44$",
        )
        self.assertIn(
            f"Удобное время связи: {lead.preferred_contact_time}",
            confirmation,
        )

    def test_repair_answer_explains_price_naturally(self) -> None:
        """Проверяет полезное объяснение стоимости."""
        session_id = "dialogue-natural-price"
        self._chat(
            session_id,
            "Хочу оформить заявку на ремонт кондиционера",
        )
        response = self._chat(session_id, "Не включается")

        self.assertIn("150–250 ₪", response)
        self.assertIn("консультации со специалистом", response)
        self.assertIn("модели кондиционера", response)
        self.assertIn("сложности доступа", response)
        self.assertEqual(response.count("?"), 1)

    def test_cleaning_dialogue_keeps_context_after_phone(self) -> None:
        """Проверяет сохранение контекста чистки."""
        session_id = "dialogue-cleaning-context"
        cleaning_response = self._chat(
            session_id,
            "Хочу оформить заявку на чистку кондиционера",
        )
        self.assertIn("плановая чистка", cleaning_response)

        problem_response = self._chat(
            session_id,
            "Слабый поток воздуха",
        )
        self.assertEqual(problem_response, ASK_CITY)

        self.assertEqual(self._chat(session_id, "Ашдод"), ASK_NAME)
        self.assertEqual(self._chat(session_id, "Максим"), ASK_CONTACT)

        contact_response = self._chat(session_id, "0505767675")
        self.assertIn("Максим, спасибо, телефон записал", contact_response)
        self.assertIn("чистка кондиционера", contact_response)
        self.assertIn("Ашдод", contact_response)
        self.assertIn("Слабый поток воздуха", contact_response)
        self.assertIn("Когда вам удобно", contact_response)
        self.assertNotIn("Какая услуга", contact_response)
        self.assertNotIn("плановая чистка или", contact_response)

        confirmation = self._chat(session_id, "Завтра утром")
        self.assertIn("Заявка оформлена.", confirmation)
        self.assertIn("Услуга: чистка кондиционера", confirmation)
        self.assertIn("Проблема: Слабый поток воздуха", confirmation)
        self.assertIn("Город: Ашдод", confirmation)
        self.assertIn("Контакт: +972505767675", confirmation)
        self.assertIn("Удобное время связи: Завтра утром", confirmation)

        lead = get_lead_by_session_id(self.db, session_id)
        self.assertEqual(lead.name, "Максим")
        self.assertEqual(lead.phone, "+972505767675")
        self.assertEqual(lead.preferred_contact_time, "Завтра утром")

        addition_response = self._chat(
            session_id,
            "Еще появился запах",
        )
        self.assertEqual(
            addition_response,
            "Спасибо. Добавил эту информацию к вашей заявке.",
        )
        self.assertIn(
            "Еще появился запах",
            get_lead_by_session_id(self.db, session_id).message,
        )

    def test_known_fields_are_not_requested_again(self) -> None:
        """Проверяет переход сразу к единственному недостающему полю."""
        response = self._chat(
            "known-fields",
            (
                "Хочу оформить заявку на чистку кондиционера. "
                "Слабый поток воздуха, Ашдод. Максим 0505767675"
            ),
        )

        self.assertIn("Максим, спасибо, телефон записал", response)
        self.assertIn("чистка кондиционера", response)
        self.assertIn("Ашдод", response)
        self.assertIn("Слабый поток воздуха", response)
        self.assertIn("Когда вам удобно", response)
        self.assertNotIn("Какая услуга", response)
        self.assertNotIn("В каком городе", response)
        self.assertNotIn("Как к вам обращаться", response)
        self.assertNotIn("Оставьте, пожалуйста", response)

    def _reach_contact_step(self, session_id: str) -> None:
        """Проводит диалог до запроса контакта."""
        self._chat(
            session_id,
            "Хочу оформить заявку на ремонт кондиционера",
        )
        self._chat(session_id, "Не включается")
        self.assertEqual(self._chat(session_id, "Ашкелон"), ASK_NAME)
        self.assertEqual(self._chat(session_id, "Игорь"), ASK_CONTACT)

    def _create_repair_lead(self, session_id: str) -> None:
        """Создает типовую заявку на ремонт."""
        self._reach_contact_step(session_id)
        self.assertEqual(
            self._chat(session_id, "0521234567"),
            ASK_CONTACT_TIME,
        )
        confirmation = self._chat(session_id, "В рабочее время")
        self.assertIn("Заявка оформлена.", confirmation)

    def _chat(self, session_id: str, message: str) -> str:
        """Собирает потоковый ответ в строку."""

        async def collect() -> str:
            """Асинхронно считывает части ответа."""
            stream = stream_chat_answer(
                db=self.db,
                llm_client=object(),
                session_id=session_id,
                user_message=message,
            )
            return "".join([chunk async for chunk in stream])

        return asyncio.run(collect())

    def _chat_with_update_check(
        self,
        session_id: str,
        message: str,
    ) -> str | None:
        """Проверяет добавление сведений в лид."""
        lead = get_lead_by_session_id(self.db, session_id)
        return add_details_to_existing_lead(
            db=self.db,
            lead=lead,
            user_message=message,
        )


if __name__ == "__main__":
    unittest.main()
