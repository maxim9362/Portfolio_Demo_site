# Этот файл проверяет короткие естественные ответы на small talk.

import asyncio
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.rag.retriever import RetrievedChunk
from app.repositories.lead_repository import get_lead_by_session_id
from app.repositories.message_repository import save_message
from app.services.chat_service import stream_chat_answer
from app.services.conversation_responder import get_conversation_response
from app.services.lead_dialogue import (
    ASK_CONTACT,
    ASK_CONTACT_TIME,
    ASK_NAME,
    BOOKING_DECLINED,
    CLARIFY_CONTACT,
    CLARIFY_PROBLEM,
)
from app.services.lead_extractor import extract_service
from app.services.session_service import get_or_create_session


class SmallTalkTests(unittest.TestCase):
    """Проверяет приветствия, вопросы о боте и составные сообщения."""

    def setUp(self) -> None:
        """Создает изолированную базу сообщений."""
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def tearDown(self) -> None:
        """Освобождает ресурсы тестовой базы."""
        self.db.close()
        self.engine.dispose()

    def test_greetings_receive_short_answer(self) -> None:
        """Проверяет единый короткий ответ на приветствия."""
        for message in (
            "привет",
            "Здравствуйте!",
            "добрый день",
            "добрый вечер",
            "хай",
            "приветик",
        ):
            with self.subTest(message=message):
                self.assertEqual(
                    get_conversation_response(message),
                    "Здравствуйте! Чем могу помочь?",
                )

    def test_wellbeing_questions_receive_natural_answer(self) -> None:
        """Проверяет ответ на короткий вопрос о делах."""
        for message in ("как дела", "Как поживаешь?"):
            with self.subTest(message=message):
                self.assertEqual(
                    get_conversation_response(message),
                    "Спасибо, все хорошо. Чем могу помочь?",
                )

    def test_working_hours_question_receives_exact_schedule(self) -> None:
        """Проверяет ответ на вопрос о работе в пятницу."""
        response = get_conversation_response(
            "Работаете ли вы в пятницу?"
        )

        self.assertIn("пятница 09:00–13:00", response)
        self.assertIn("суббота — выходной", response)

    def test_identity_questions_explain_bot_role(self) -> None:
        """Проверяет краткое описание возможностей консультанта."""
        for message in ("кто ты", "что ты умеешь?"):
            with self.subTest(message=message):
                self.assertEqual(
                    get_conversation_response(message),
                    (
                        "Я AI-консультант компании. Могу рассказать об "
                        "услугах, ценах и помочь оформить заявку."
                    ),
                )

    def test_greeting_with_question_is_answered_by_business_logic(self) -> None:
        """Проверяет, что приветствие не скрывает вопрос об услуге."""
        llm_client = StreamingLLMStub(
            "Чистка стоит ориентировочно 250–400 ₪."
        )
        with (
            patch("app.services.chat_service.EmbeddingClient"),
            patch("app.services.chat_service.KnowledgeRetriever") as retriever,
        ):
            retriever.return_value.retrieve.return_value = [
                RetrievedChunk(
                    content="Чистка стоит 250–400 ₪.",
                    source="prices/air_conditioner_prices.md",
                    distance=0.1,
                )
            ]
            response = self._chat(
                "small-talk-business-question",
                "Привет, сколько стоит чистка кондиционера?",
                llm_client=llm_client,
            )

        self.assertIn("250–400 ₪", response)
        self.assertNotEqual(response, "Здравствуйте! Чем могу помочь?")
        self.assertEqual(llm_client.call_count, 1)

    def test_cleaning_price_request_uses_meaning_before_form(self) -> None:
        """Проверяет распознавание чистки и приоритет содержательного ответа."""
        message = "Хочу почистить кондиционер, хочу узнать стоимость"
        self.assertEqual(
            extract_service(message),
            "чистка кондиционера",
        )

        llm_client = StreamingLLMStub(
            "Чистка стоит ориентировочно 250–400 ₪. "
            "Точная цена зависит от состояния и доступа. "
            "Это плановая чистка или уже есть проблема?"
        )
        with (
            patch("app.services.chat_service.EmbeddingClient"),
            patch("app.services.chat_service.KnowledgeRetriever") as retriever,
        ):
            retriever.return_value.retrieve.return_value = [
                RetrievedChunk(
                    content=(
                        "Профилактическая чистка стоит 250–400 ₪. "
                        "Цена зависит от состояния и доступа."
                    ),
                    source="prices/air_conditioner_prices.md",
                    distance=0.1,
                )
            ]
            response = self._chat(
                "cleaning-price-meaning",
                message,
                llm_client=llm_client,
            )

        self.assertIn("250–400 ₪", response)
        self.assertNotIn("Что именно нужно", response)
        self.assertNotIn("Какая услуга", response)
        self.assertIn(
            "Услуга: чистка кондиционера",
            llm_client.system_prompt,
        )

    def test_accepting_llm_offer_continues_lead_collection(self) -> None:
        """Проверяет запуск state machine после полезного ответа LLM."""
        session_id = "accepted-llm-offer"
        get_or_create_session(self.db, session_id)
        save_message(
            self.db,
            session_id,
            "user",
            "Хочу почистить кондиционер",
        )
        save_message(
            self.db,
            session_id,
            "assistant",
            (
                "Чистка помогает удалить пыль и загрязнения. "
                "Хотите, я оформлю заявку мастеру?"
            ),
        )

        response = self._chat(session_id, "Да")

        self.assertIn("плановая чистка", response)
        self.assertNotIn("Какая услуга", response)

    def test_contact_data_without_consent_does_not_create_lead(self) -> None:
        """Проверяет запрет автоматической заявки без согласия клиента."""
        session_id = "contacts-without-consent"
        llm_client = StreamingLLMStub(
            "Чистка стоит ориентировочно 250–400 ₪."
        )
        with (
            patch("app.services.chat_service.EmbeddingClient"),
            patch("app.services.chat_service.KnowledgeRetriever") as retriever,
        ):
            retriever.return_value.retrieve.return_value = [
                RetrievedChunk(
                    content="Чистка стоит 250–400 ₪.",
                    source="prices/air_conditioner_prices.md",
                    distance=0.1,
                )
            ]
            self._chat(
                session_id,
                (
                    "Меня зовут Максим, телефон 0505767675. "
                    "Завтра утром. Сколько стоит чистка кондиционера?"
                ),
                llm_client=llm_client,
            )

        self.assertIsNone(get_lead_by_session_id(self.db, session_id))

    def test_new_breakdown_does_not_resume_stale_contact_collection(
        self,
    ) -> None:
        """Проверяет новый запрос после незавершенной старой заявки."""
        session_id = "stale-contact-cycle"
        get_or_create_session(self.db, session_id)
        for role, content in (
            (
                "user",
                "Хочу оформить заявку на ремонт кондиционера",
            ),
            ("assistant", "Что именно происходит с кондиционером: не охлаждает, течет вода, шумит, пахнет, не включается или показывает ошибку?"),
            ("user", "Не охлаждает"),
            (
                "assistant",
                "Понял. Причиной могут быть загрязнение или недостаток газа. В каком городе находится кондиционер?",
            ),
            ("user", "Явне"),
            (
                "assistant",
                "В Явне мы работаем. Хотите, я оформлю заявку мастеру?",
            ),
            ("user", "Да"),
            ("assistant", "Как к вам обращаться?"),
            ("user", "Максим"),
            (
                "assistant",
                "Оставьте, пожалуйста, номер телефона или email для связи.",
            ),
        ):
            save_message(self.db, session_id, role, content)

        first_response = self._chat(
            session_id,
            "Привет. У меня сломался кондиционер",
        )
        second_response = self._chat(session_id, "4кав")
        third_response = self._chat(session_id, "0503456554")

        self.assertIn("Что именно происходит", first_response)
        self.assertNotIn("номер телефона", first_response)
        self.assertEqual(second_response, CLARIFY_PROBLEM)
        self.assertEqual(third_response, CLARIFY_PROBLEM)
        self.assertIsNone(get_lead_by_session_id(self.db, session_id))

    def test_llm_city_question_accepts_unlisted_location(self) -> None:
        """Проверяет переход от ответа LLM к подтверждению зоны выезда."""
        session_id = "llm-unlisted-location"
        llm_client = StreamingLLMStub(
            "Если кондиционер не включается, нужна диагностика. "
            "Ремонт обычно начинается от 250 ₪, а точная цена зависит "
            "от поломки, модели и доступа. В каком городе находится "
            "кондиционер?"
        )
        with (
            patch("app.services.chat_service.EmbeddingClient"),
            patch("app.services.chat_service.KnowledgeRetriever") as retriever,
        ):
            retriever.return_value.retrieve.return_value = [
                RetrievedChunk(
                    content="Ремонт начинается примерно от 250 ₪.",
                    source="prices/air_conditioner_prices.md",
                    distance=0.1,
                )
            ]
            first_response = self._chat(
                session_id,
                "Привет. У меня не включается кондей",
                llm_client=llm_client,
            )

        second_response = self._chat(session_id, "Мароша")

        self.assertIn("В каком городе", first_response)
        self.assertIn("Мароша не входит в основной список", second_response)
        self.assertIn("может находиться в зоне выезда", second_response)
        self.assertIn("Хотите, я оформлю заявку", second_response)
        self.assertNotIn("не обслуживаем", second_response)
        self.assertIsNone(get_lead_by_session_id(self.db, session_id))

    def test_installation_price_is_not_repeated_after_city(self) -> None:
        """Проверяет переход от цены установки к предложению заявки."""
        session_id = "installation-price-city"
        get_or_create_session(self.db, session_id)
        save_message(
            self.db,
            session_id,
            "user",
            "Сколько стоит установка кондиционера?",
        )
        save_message(
            self.db,
            session_id,
            "assistant",
            (
                "Установка начинается примерно от 900 ₪. "
                "В каком городе планируется установка?"
            ),
        )

        city_response = self._chat(session_id, "Ашкелон")
        decline_response = self._chat(
            session_id,
            "нет, пока только узнаю",
        )

        self.assertIn("Хотите, я оформлю заявку", city_response)
        self.assertNotIn("начинается примерно от 900", city_response)
        self.assertEqual(decline_response, BOOKING_DECLINED)

    def test_accepted_offer_remains_active_until_lead_is_created(self) -> None:
        """Проверяет сохранение шага заявки после нескольких сообщений."""
        session_id = "persistent-accepted-offer"
        get_or_create_session(self.db, session_id)
        for role, content in (
            ("user", "Не охлаждает"),
            (
                "assistant",
                "Причин может быть несколько. В каком городе вы находитесь?",
            ),
            ("user", "Явне"),
            (
                "assistant",
                "В Явне мы работаем. Хотите, я оформлю заявку мастеру?",
            ),
        ):
            save_message(self.db, session_id, role, content)

        self.assertEqual(self._chat(session_id, "Да"), ASK_NAME)
        self.assertEqual(self._chat(session_id, "Максим"), ASK_CONTACT)
        self.assertEqual(
            self._chat(session_id, "05043343443"),
            CLARIFY_CONTACT,
        )
        self.assertEqual(
            self._chat(session_id, "0504334344"),
            ASK_CONTACT_TIME,
        )

        confirmation = self._chat(session_id, "13:43")
        lead = get_lead_by_session_id(self.db, session_id)

        self.assertIn("Заявка оформлена.", confirmation)
        self.assertIsNotNone(lead)
        self.assertEqual(lead.name, "Максим")
        self.assertEqual(lead.phone, "+972504334344")
        self.assertRegex(
            lead.preferred_contact_time,
            r"^(?:сегодня|завтра) в 13:43$",
        )

    def _chat(
        self,
        session_id: str,
        message: str,
        llm_client: object | None = None,
    ) -> str:
        """Собирает потоковый ответ сервиса в строку."""

        async def collect() -> str:
            """Считывает все части ответа текущего запроса."""
            stream = stream_chat_answer(
                db=self.db,
                llm_client=llm_client or object(),
                session_id=session_id,
                user_message=message,
            )
            return "".join([chunk async for chunk in stream])

        return asyncio.run(collect())


class StreamingLLMStub:
    """Имитирует потоковый LLM-ответ без внешнего API."""

    def __init__(self, answer: str) -> None:
        """Сохраняет ответ и счетчик вызовов."""
        self.answer = answer
        self.call_count = 0
        self.system_prompt = ""

    async def stream_answer(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
    ):
        """Возвращает один фрагмент заранее заданного ответа."""
        self.call_count += 1
        self.system_prompt = system_prompt
        yield self.answer


if __name__ == "__main__":
    unittest.main()
