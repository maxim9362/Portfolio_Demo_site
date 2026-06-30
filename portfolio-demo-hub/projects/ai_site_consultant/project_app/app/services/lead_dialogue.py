# Этот файл ведет клиента по шагам оформления заявки на обслуживание кондиционера.

from collections.abc import Sequence
from dataclasses import dataclass
import re
from typing import Protocol

from sqlalchemy.orm import Session

from app.repositories.lead_repository import get_lead_by_session_id
from app.services.lead_extractor import (
    extract_city as extract_city_value,
    extract_email,
    extract_phone,
    extract_preferred_contact_time,
    extract_problem as extract_problem_value,
    extract_service,
    is_incomplete_contact_time,
    normalize_air_conditioner_text,
)
from app.services.lead_service import (
    create_or_update_lead,
    format_lead_confirmation,
)
from app.services.lead_state import build_lead_state


class DialogueMessage(Protocol):
    """Описывает сообщение, используемое пошаговой логикой лида."""
    role: str
    content: str


LEAD_INTENT_PATTERN = re.compile(
    r"(?:\b(?:записаться|запишите|заявк\w*|перезвон\w*|"
    r"оформить|оформите|оформляйте)\b|"
    r"связаться\s+со\s+(?:специалист\w*|мастер\w*)|"
    r"(?:вызвать|пришлите|нужен)\s+(?:мастер\w*|техник\w*))",
    re.IGNORECASE,
)
NEW_REPAIR_REQUEST_PATTERN = re.compile(
    r"(?=.*\bкондиционер\b)"
    r"(?=.*\b(?:сломал\w*|поломал\w*|перестал\s+работать)\b)",
    re.IGNORECASE,
)
POSSIBLE_LOCATION_PATTERN = re.compile(
    r"^[А-ЯЁA-Z][А-ЯЁA-Zа-яёa-z-]{1,39}"
    r"(?:\s+[А-ЯЁA-Zа-яёa-z-]{2,39}){0,2}$",
    re.IGNORECASE,
)
NON_LOCATION_ANSWERS = {
    "да",
    "нет",
    "не знаю",
    "не уверен",
    "не уверена",
    "рядом",
    "далеко",
    "здесь",
    "там",
}
BOOKING_OFFER_PATTERN = re.compile(
    r"(?:хотите|можете|давайте).{0,40}"
    r"(?:оформ\w*\s+заявк\w*|вызов\w*\s+мастер\w*|"
    r"запис\w*\s+мастер\w*)",
    re.IGNORECASE,
)
SIMPLE_NAME_PATTERN = re.compile(
    r"^[А-ЯЁA-Z][а-яёa-z]{1,30}"
    r"(?:[\s-][А-ЯЁA-Z][а-яёa-z]{1,30}){0,2}$",
    re.IGNORECASE,
)
PRICE_PATTERN = re.compile(r"\b(?:цен\w*|стоит|стоимость|сколько)\b", re.IGNORECASE)
PLAN_CLEANING_PATTERN = re.compile(
    r"\b(?:планов\w*\s+чистк\w*|профилактическ\w*\s+чистк\w*|"
    r"для\s+профилактик\w*|без\s+проблем\w*)\b",
    re.IGNORECASE,
)
AFFIRMATIVE_PATTERN = re.compile(
    r"^(?:да|давайте|хочу|оформляйте|оформить|запишите|можно|хорошо|ок|окей)"
    r"[!,.?\s]*$",
    re.IGNORECASE,
)
NEGATIVE_PATTERN = re.compile(
    r"^(?:нет(?:\s*[,.-]?\s*пока.*)?|не\s+нужно|не\s+сейчас|"
    r"пока\s+(?:нет|только\s+узнаю)|только\s+узнаю|отмена)[!,.?\s]*$",
    re.IGNORECASE,
)
ASK_TASK = (
    "Конечно, помогу. Что именно нужно: ремонт, установка, чистка, "
    "заправка газа, диагностика или демонтаж кондиционера?"
)
ASK_PROBLEM = (
    "Понял, давайте разберемся. Что именно происходит с кондиционером: "
    "он не охлаждает, течет, шумит, пахнет, не включается или показывает "
    "ошибку?"
)
REPAIR_PRICE_AND_PROBLEM = (
    "Обычно ремонт кондиционера начинается примерно от 250 ₪. "
    "Точную стоимость можно узнать после консультации со специалистом или "
    "проверки мастером: она зависит от причины поломки, модели кондиционера "
    "и сложности доступа. "
    "Что именно происходит: не охлаждает, течет, шумит или не включается?"
)
DIAGNOSTICS_PRICE_AND_CITY = (
    "Выезд и диагностика обычно стоят примерно 150–250 ₪. "
    "Точную стоимость можно узнать после консультации со специалистом или "
    "проверки мастером: она зависит от причины проблемы, модели кондиционера "
    "и сложности доступа. Подскажите, пожалуйста, в каком городе нужен мастер?"
)
CLEANING_PRICE_AND_PROBLEM = (
    "Профилактическая чистка обычно стоит примерно 250–400 ₪. "
    "Если кондиционер слабо дует, причиной могут быть загрязненные фильтры, "
    "испаритель или вентилятор. Это плановая чистка или уже есть проблема, "
    "например слабый поток воздуха, запах или течь?"
)
CLEANING_PROBLEM_QUESTION = (
    "Это плановая чистка или уже есть проблема, например слабый поток "
    "воздуха, запах или течь?"
)
GAS_PRICE_AND_CITY = (
    "Заправка газа обычно стоит примерно 350–600 ₪. "
    "Точную стоимость можно узнать после проверки специалистом: она зависит "
    "от модели, типа газа, объема и наличия утечки. "
    "Подскажите, пожалуйста, в каком городе находится кондиционер?"
)
INSTALLATION_PRICE_AND_CITY = (
    "Стандартная установка начинается примерно от 900 ₪. "
    "Точную стоимость можно узнать после консультации со специалистом: она "
    "зависит от модели, длины трассы, стены и сложности доступа. "
    "Подскажите, пожалуйста, в каком городе планируется установка?"
)
DISMANTLING_PRICE_AND_CITY = (
    "Демонтаж обычно стоит примерно 300–600 ₪. "
    "Точную стоимость можно узнать после проверки специалистом: она зависит "
    "от модели, высоты, крепления и сложности доступа. "
    "Подскажите, пожалуйста, в каком городе находится объект?"
)
PRICE_PROMPTS = {
    "ремонт кондиционера": REPAIR_PRICE_AND_PROBLEM,
    "диагностика кондиционера": DIAGNOSTICS_PRICE_AND_CITY,
    "чистка кондиционера": CLEANING_PRICE_AND_PROBLEM,
    "заправка газа": GAS_PRICE_AND_CITY,
    "установка кондиционера": INSTALLATION_PRICE_AND_CITY,
    "демонтаж кондиционера": DISMANTLING_PRICE_AND_CITY,
}
ASK_CITY = (
    "В каком городе находится кондиционер: Ашдод, Ашкелон, "
    "Ган-Явне, Явне или Кирьят-Малахи?"
)
OFFER_BOOKING = (
    "Мы работаем в этом городе. Хотите, я оформлю заявку мастеру "
    "для уточнения стоимости и времени выезда?"
)
PROVISIONAL_AREA_OFFER = (
    "{city} не входит в основной список городов, но может находиться в зоне "
    "выезда мастера. Хотите, я оформлю заявку, чтобы менеджер подтвердил "
    "возможность выезда?"
)
BOOKING_DECLINED = (
    "Хорошо, заявку пока не оформляю. Можете продолжить задавать вопросы, "
    "я постараюсь помочь."
)
ASK_NAME = "Как к вам обращаться?"
ASK_CONTACT = "Оставьте, пожалуйста, номер телефона или email для связи."
CONTACT_TIME_QUESTION = (
    "Когда вам удобно, чтобы мастер или менеджер с вами связался? "
    "Например: сегодня после 17:00, завтра утром или в любое время."
)
ASK_CONTACT_TIME = CONTACT_TIME_QUESTION
CLARIFY_TASK = (
    "Не совсем понял услугу. Напишите один вариант: ремонт, установка, "
    "чистка, заправка газа, диагностика или демонтаж."
)
CLARIFY_PROBLEM = (
    "Не совсем понял, что произошло. Подскажите, пожалуйста: кондиционер "
    "не охлаждает, течет, шумит, пахнет, не включается или показывает ошибку?"
)
CLARIFY_CITY = (
    "Не совсем понял название населенного пункта. Напишите, пожалуйста, "
    "город, поселок или кибуц, где находится кондиционер."
)
CLARIFY_NAME = "Не удалось распознать имя. Напишите, пожалуйста, только ваше имя."
CLARIFY_CONTACT = (
    "Не удалось распознать контакт. Укажите корректный израильский мобильный "
    "номер, например 0501234567 или +972501234567, либо email."
)
CLARIFY_CONTACT_TIME = (
    "Не удалось распознать удобное время. Напишите, например: завтра утром, "
    "сегодня после 17:00, в воскресенье или в любое время."
)
CLARIFY_INCOMPLETE_CONTACT_TIME = (
    "Уточните, пожалуйста, время. Например: 13:30 или 14:00."
)
LEAD_CREATED = "Заявка оформлена."


@dataclass(frozen=True, slots=True)
class LeadDialogueState:
    """Хранит восстановленное состояние текущего цикла оформления."""
    active: bool
    service: str | None
    problem: str | None
    city: str | None
    name: str | None
    phone: str | None
    email: str | None
    preferred_contact_time: str | None
    expected_step: str | None
    price_requested: bool
    price_answered: bool
    booking_offered: bool
    booking_confirmed: bool
    booking_declined: bool
    city_requires_confirmation: bool


def process_lead_dialogue(
    db: Session,
    session_id: str,
    messages: Sequence[DialogueMessage],
) -> str | None:
    """Выбирает следующий вопрос или создает готовую заявку."""
    existing_lead = get_lead_by_session_id(db, session_id)
    if existing_lead is not None:
        return None

    cycle = _current_dialogue_cycle(messages)
    if not cycle:
        return None

    state = _build_state(cycle, context_messages=cycle)
    if not state.active:
        return None

    latest_user_message = next(
        (
            message.content.strip()
            for message in reversed(cycle)
            if message.role == "user"
        ),
        "",
    )

    if not state.service:
        return CLARIFY_TASK if state.expected_step == "task" else ASK_TASK

    if (
        state.price_requested
        and not state.price_answered
        and not state.city
        and state.service in PRICE_PROMPTS
        and state.service != "ремонт кондиционера"
    ):
        return PRICE_PROMPTS[state.service]

    if state.service == "ремонт кондиционера" and not state.problem:
        if state.expected_step == "problem":
            return CLARIFY_PROBLEM
        return REPAIR_PRICE_AND_PROBLEM if state.price_requested else ASK_PROBLEM

    cleaning_with_problem = (
        state.service == "чистка кондиционера"
        and state.problem is not None
    )
    if state.service == "чистка кондиционера" and not state.problem:
        return (
            CLEANING_PRICE_AND_PROBLEM
            if state.price_requested
            else CLEANING_PROBLEM_QUESTION
        )

    if cleaning_with_problem:
        if state.booking_declined:
            return BOOKING_DECLINED
        if not state.booking_confirmed:
            if not state.booking_offered:
                return (
                    f"{_cleaning_problem_help_response(state.problem)} "
                    f"{OFFER_BOOKING}"
                )
            if state.expected_step == "booking":
                return None
            return OFFER_BOOKING
        if not state.city:
            return (
                CLARIFY_CITY
                if state.expected_step == "city"
                else ASK_CITY
            )

    if not state.city:
        if state.expected_step == "city":
            return CLARIFY_CITY
        if state.problem:
            return _problem_help_response(state.problem)
        if state.price_requested and state.service in PRICE_PROMPTS:
            return PRICE_PROMPTS[state.service]
        return ASK_CITY

    if state.city_requires_confirmation and not state.booking_offered:
        return PROVISIONAL_AREA_OFFER.format(city=state.city)

    if not cleaning_with_problem:
        if state.booking_declined:
            return BOOKING_DECLINED

        if not state.booking_confirmed:
            if not state.booking_offered:
                if state.city_requires_confirmation:
                    return PROVISIONAL_AREA_OFFER.format(city=state.city)
                return (
                    f"Отлично, {state.city} входит в нашу зону обслуживания. "
                    f"{OFFER_BOOKING}"
                )
            if state.expected_step == "booking":
                return None
            return OFFER_BOOKING

    if not state.name:
        return CLARIFY_NAME if state.expected_step == "name" else ASK_NAME

    if not (state.phone or state.email):
        return CLARIFY_CONTACT if state.expected_step == "contact" else ASK_CONTACT

    if not state.preferred_contact_time:
        if (
            state.expected_step == "contact_time"
            and is_incomplete_contact_time(latest_user_message)
        ):
            return CLARIFY_INCOMPLETE_CONTACT_TIME
        if cleaning_with_problem:
            contact_recorded = (
                "телефон записал"
                if state.phone
                else "email записал"
            )
            known_request = (
                f"Я вижу, что нужна {state.service} в городе {state.city}, "
                f"проблема — {state.problem}. "
            )
            return (
                f"{state.name}, спасибо, {contact_recorded}. "
                f"{known_request}{CONTACT_TIME_QUESTION}"
            )
        return (
            CLARIFY_CONTACT_TIME
            if state.expected_step == "contact_time"
            else ASK_CONTACT_TIME
        )

    details = (
        f"Услуга: {state.service}. "
        f"Проблема: {state.problem or latest_user_message}. "
        f"Город: {state.city}. "
        + (
            "Зона выезда: требует подтверждения менеджером."
            if state.city_requires_confirmation
            else "Зона выезда: подтверждена."
        )
    )
    lead = create_or_update_lead(
        db=db,
        session_id=session_id,
        name=state.name,
        phone=state.phone,
        email=state.email,
        details=details,
        preferred_contact_time=state.preferred_contact_time,
    )
    return format_lead_confirmation(lead)


def _current_dialogue_cycle(
    messages: Sequence[DialogueMessage],
) -> list[DialogueMessage]:
    """Выделяет актуальный цикл оформления из полной истории."""
    normalized_messages = [
        (
            message,
            normalize_air_conditioner_text(message.content),
        )
        for message in messages
    ]
    last_completion_index = max(
        (
            index
            for index, (message, _) in enumerate(normalized_messages)
            if message.role == "assistant"
            and (
                LEAD_CREATED in message.content
                or message.content == BOOKING_DECLINED
            )
        ),
        default=-1,
    )
    explicit_start_index = max(
        (
            index
            for index, (message, normalized_content) in enumerate(
                normalized_messages
            )
            if index > last_completion_index
            and message.role == "user"
            and LEAD_INTENT_PATTERN.search(normalized_content)
        ),
        default=-1,
    )
    new_repair_start_index = max(
        (
            index
            for index, (message, normalized_content) in enumerate(
                normalized_messages
            )
            if index > last_completion_index
            and message.role == "user"
            and NEW_REPAIR_REQUEST_PATTERN.search(normalized_content)
        ),
        default=-1,
    )
    offered_start_index = _booking_offer_cycle_start(
        messages,
        last_completion_index,
    )
    city_question_start_index = _city_question_cycle_start(
        messages,
        last_completion_index,
    )
    state_machine_start_index = max(
        explicit_start_index,
        new_repair_start_index,
        offered_start_index,
    )
    start_index = (
        state_machine_start_index
        if state_machine_start_index != -1
        else city_question_start_index
    )
    if start_index == -1:
        return []
    return list(messages[start_index:])


def _city_question_cycle_start(
    messages: Sequence[DialogueMessage],
    last_completion_index: int,
) -> int:
    """Подхватывает state machine после вопроса LLM о городе."""
    city_prompt_index = max(
        (
            index
            for index in range(last_completion_index + 1, len(messages))
            if messages[index].role == "assistant"
            and _step_for_prompt(messages[index].content) == "city"
            and _next_user_message(messages, index + 1) is not None
        ),
        default=-1,
    )
    if city_prompt_index == -1:
        return -1

    return next(
        (
            index
            for index in range(
                city_prompt_index - 1,
                last_completion_index,
                -1,
            )
            if messages[index].role == "user"
            and (
                extract_service(messages[index].content) is not None
                or extract_problem_value(messages[index].content) is not None
            )
        ),
        city_prompt_index,
    )


def _booking_offer_cycle_start(
    messages: Sequence[DialogueMessage],
    last_completion_index: int,
) -> int:
    """Находит начало диалога, если пользователь принял предложение заявки."""
    accepted_offer_index = -1
    for index in range(len(messages) - 1, last_completion_index, -1):
        message = messages[index]
        if (
            message.role != "assistant"
            or not BOOKING_OFFER_PATTERN.search(message.content)
        ):
            continue

        answer = _next_user_message(messages, index + 1)
        if answer is not None and AFFIRMATIVE_PATTERN.fullmatch(answer):
            accepted_offer_index = index
            break

    if accepted_offer_index == -1:
        return -1

    return next(
        (
            index
            for index in range(
                accepted_offer_index - 1,
                last_completion_index,
                -1,
            )
            if messages[index].role == "user"
            and (
                extract_service(messages[index].content) is not None
                or extract_problem_value(messages[index].content) is not None
            )
        ),
        accepted_offer_index,
    )


def _build_state(
    messages: Sequence[DialogueMessage],
    context_messages: Sequence[DialogueMessage] | None = None,
) -> LeadDialogueState:
    """Восстанавливает шаги формы из сообщений текущего цикла."""
    user_messages = [
        message.content.strip()
        for message in messages
        if message.role == "user" and message.content.strip()
    ]
    base_state = build_lead_state(context_messages or messages)
    service = base_state.service
    problem = base_state.problem
    city = base_state.city
    name = base_state.name
    phone = base_state.phone
    email = base_state.email
    preferred_contact_time = base_state.preferred_contact_time
    expected_step: str | None = None
    booking_offered = False
    booking_confirmed = any(
        LEAD_INTENT_PATTERN.search(
            normalize_air_conditioner_text(message)
        )
        for message in user_messages
    )
    booking_declined = False
    city_requires_confirmation = False

    for index, message in enumerate(messages):
        if message.role != "assistant":
            continue

        step = _step_for_prompt(message.content)
        if step is None:
            continue

        expected_step = step
        if step == "booking":
            booking_offered = True
        answer = _next_user_message(messages, index + 1)
        if answer is None:
            continue

        if step == "task":
            parsed_service = extract_service(answer)
            if parsed_service and parsed_service != "консультация":
                service = parsed_service
                expected_step = None
        elif step == "problem":
            parsed_problem = _extract_problem(answer)
            if (
                parsed_problem is None
                and service == "чистка кондиционера"
                and PLAN_CLEANING_PATTERN.search(answer)
            ):
                parsed_problem = "плановая чистка"
            if parsed_problem:
                problem = parsed_problem
                expected_step = None
        elif step == "city":
            parsed_city = _extract_city(answer)
            if parsed_city:
                city = parsed_city
                city_requires_confirmation = False
                expected_step = None
            else:
                possible_location = _extract_possible_location(answer)
                if possible_location:
                    city = possible_location
                    city_requires_confirmation = True
                    expected_step = None
        elif step == "name":
            parsed_name = _parse_name_answer(answer)
            if parsed_name:
                name = parsed_name
                expected_step = None
        elif step == "contact":
            phone = phone or extract_phone(answer)
            email = email or extract_email(answer)
            if phone or email:
                expected_step = None
        elif step == "contact_time":
            parsed_contact_time = extract_preferred_contact_time(answer)
            if parsed_contact_time:
                preferred_contact_time = parsed_contact_time
                expected_step = None
        elif step == "booking":
            if AFFIRMATIVE_PATTERN.fullmatch(answer):
                booking_confirmed = True
                expected_step = None
            elif NEGATIVE_PATTERN.fullmatch(answer):
                booking_declined = True
                expected_step = None

    return LeadDialogueState(
        active=True,
        service=service,
        problem=problem,
        city=city,
        name=name,
        phone=phone,
        email=email,
        preferred_contact_time=preferred_contact_time,
        expected_step=expected_step,
        price_requested=any(PRICE_PATTERN.search(message) for message in user_messages),
        price_answered=any(
            message.role == "assistant"
            and message.content in PRICE_PROMPTS.values()
            for message in messages
        ),
        booking_offered=booking_offered,
        booking_confirmed=booking_confirmed,
        booking_declined=booking_declined,
        city_requires_confirmation=city_requires_confirmation,
    )


def _step_for_prompt(content: str) -> str | None:
    """Определяет поле, которое запрашивал предыдущий ответ."""
    if (
        content == OFFER_BOOKING
        or content.endswith(OFFER_BOOKING)
        or BOOKING_OFFER_PATTERN.search(content)
    ):
        return "booking"

    prompts = {
        ASK_TASK: "task",
        CLARIFY_TASK: "task",
        ASK_PROBLEM: "problem",
        REPAIR_PRICE_AND_PROBLEM: "problem",
        DIAGNOSTICS_PRICE_AND_CITY: "city",
        CLEANING_PRICE_AND_PROBLEM: "problem",
        CLEANING_PROBLEM_QUESTION: "problem",
        GAS_PRICE_AND_CITY: "city",
        INSTALLATION_PRICE_AND_CITY: "city",
        DISMANTLING_PRICE_AND_CITY: "city",
        CLARIFY_PROBLEM: "problem",
        ASK_CITY: "city",
        CLARIFY_CITY: "city",
        ASK_NAME: "name",
        CLARIFY_NAME: "name",
        ASK_CONTACT: "contact",
        CLARIFY_CONTACT: "contact",
        ASK_CONTACT_TIME: "contact_time",
        CLARIFY_CONTACT_TIME: "contact_time",
        CLARIFY_INCOMPLETE_CONTACT_TIME: "contact_time",
    }
    if content.endswith(CONTACT_TIME_QUESTION):
        return "contact_time"
    normalized_content = normalize_air_conditioner_text(content)
    if (
        "в каком городе" in normalized_content
        or "каком городе" in normalized_content
    ):
        return "city"
    return prompts.get(content)


def _extract_possible_location(text: str) -> str | None:
    """Принимает произвольный город, поселок или кибуц без обещания выезда."""
    candidate = " ".join(text.strip().split())
    if candidate.casefold() in NON_LOCATION_ANSWERS:
        return None
    if not POSSIBLE_LOCATION_PATTERN.fullmatch(candidate):
        return None
    return " ".join(
        "-".join(part.capitalize() for part in word.split("-"))
        for word in candidate.split()
    )


def _problem_help_response(problem: str) -> str:
    """Дает полезную первичную информацию по симптому ремонта."""
    normalized_problem = normalize_air_conditioner_text(problem)
    if re.search(r"течет|капает", normalized_problem):
        return (
            "Понял. Течь часто связана с засором дренажа или загрязнением "
            "внутреннего блока. Устранение обычно стоит примерно 250–450 ₪, "
            "но точную стоимость можно узнать после консультации со специалистом "
            "или проверки мастером. Цена зависит от причины, модели кондиционера "
            "и сложности доступа. Подскажите, пожалуйста, в каком городе "
            "находится кондиционер?"
        )
    if re.search(r"не\s+охлаждает|слабо\s+дует|обмерз|лед", normalized_problem):
        return (
            "Понял. Причиной могут быть загрязнение, недостаток газа, датчик "
            "или внешний блок. Ремонт обычно начинается примерно от 250 ₪, "
            "но точную стоимость можно узнать после консультации со специалистом "
            "или проверки мастером. Цена зависит от причины, модели кондиционера "
            "и сложности доступа. Подскажите, пожалуйста, в каком городе "
            "находится кондиционер?"
        )
    if re.search(r"шумит|вибрирует", normalized_problem):
        return (
            "Понял. Шум часто связан с загрязнением вентилятора, креплением "
            "или износом деталей. Точную стоимость можно узнать после проверки "
            "специалистом: она зависит от причины, модели кондиционера и "
            "сложности доступа. Подскажите, пожалуйста, в каком городе "
            "находится кондиционер?"
        )
    if re.search(r"не\s+включается|выбивает|ошибк", normalized_problem):
        return (
            "Понял. Если кондиционер вообще не включается, лучше не пытаться "
            "запускать его повторно до проверки: причина может быть в питании, "
            "плате управления, пульте или компрессоре. Диагностика обычно стоит "
            "150–250 ₪, но точную стоимость ремонта можно узнать только после "
            "консультации со специалистом или проверки мастером. Цена зависит "
            "от причины поломки, модели кондиционера и сложности доступа. "
            "Подскажите, пожалуйста, в каком городе находится кондиционер?"
        )
    return (
        "Понял задачу. Для точной оценки важно учитывать модель, доступ "
        f"и состояние оборудования. {ASK_CITY}"
    )


def _cleaning_problem_help_response(problem: str) -> str:
    """Дает пояснение по проблеме, связанной с чисткой."""
    normalized_problem = normalize_air_conditioner_text(problem)
    if re.search(r"слаб\w*\s+(?:поток|дует)|плохо\s+дует", normalized_problem):
        return (
            "Слабый поток воздуха часто связан с загрязненными фильтрами, "
            "испарителем или вентилятором. Чистка обычно стоит примерно "
            "250–400 ₪, а точная стоимость зависит от модели, загрязнения "
            "и сложности доступа."
        )
    return (
        "Понял проблему. При чистке мастер проверяет фильтры, испаритель "
        "и вентилятор. Точная стоимость зависит от модели, загрязнения "
        "и сложности доступа."
    )


def _next_user_message(
    messages: Sequence[DialogueMessage],
    start_index: int,
) -> str | None:
    """Находит ответ пользователя сразу после вопроса бота."""
    for message in messages[start_index:]:
        if message.role == "assistant":
            return None
        if message.role == "user":
            return message.content.strip()
    return None


def _extract_problem(text: str) -> str | None:
    """Извлекает описание неисправности из текста."""
    return extract_problem_value(text)


def _extract_city(text: str) -> str | None:
    """Извлекает обслуживаемый город из текста."""
    return extract_city_value(text)


def _parse_name_answer(text: str) -> str | None:
    """Проверяет короткий ответ на вопрос об имени."""
    candidate = text.strip()
    if not SIMPLE_NAME_PATTERN.fullmatch(candidate):
        return None
    if (
        AFFIRMATIVE_PATTERN.fullmatch(candidate)
        or NEGATIVE_PATTERN.fullmatch(candidate)
    ):
        return None
    if _extract_city(candidate):
        return None
    return " ".join(part.capitalize() for part in candidate.split())
