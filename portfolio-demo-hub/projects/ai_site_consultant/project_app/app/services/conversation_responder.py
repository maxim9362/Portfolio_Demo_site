# Этот файл формирует локальные ответы на приветствия и неопределенные реплики.

import re

from app.services.working_hours import WORKING_HOURS_TEXT


GREETING_PATTERN = re.compile(
    r"^(?:привет|приветик|здравствуйте|здравствуй|добрый\s+(?:день|вечер|утро)|"
    r"хай|hello|hi)[!,.?\s]*$",
    re.IGNORECASE,
)
WELLBEING_PATTERN = re.compile(
    r"^(?:как\s+дела|как\s+поживаешь|как\s+поживаете)[!,.?\s]*$",
    re.IGNORECASE,
)
IDENTITY_PATTERN = re.compile(
    r"^(?:кто\s+ты|кто\s+вы|что\s+ты\s+умеешь|"
    r"что\s+вы\s+умеете)[!,.?\s]*$",
    re.IGNORECASE,
)
THANKS_PATTERN = re.compile(
    r"^(?:спасибо|благодарю|понятно|ясно|хорошо|ок|окей)[!,.?\s]*$",
    re.IGNORECASE,
)
FAREWELL_PATTERN = re.compile(
    r"^(?:пока|до\s+свидания|до\s+встречи|всего\s+доброго)[!,.?\s]*$",
    re.IGNORECASE,
)
VAGUE_PATTERN = re.compile(
    r"^(?:что|как|помоги|помощь|расскажи|можно\s+подробнее|"
    r"не\s+понял(?:а)?)[!,.?\s]*$",
    re.IGNORECASE,
)
STATUS_PATTERN = re.compile(
    r"\b(?:статус|что\s+с\s+(?:моей\s+)?заявк\w*|"
    r"заявк\w*\s+(?:принята|оформлена))\b",
    re.IGNORECASE,
)
BUSINESS_QUESTION_PATTERN = re.compile(
    r"(?:\b(?:цен\w*|стоимост\w*|сколько|почему|зачем|когда|"
    r"что\s+входит|как\s+(?:проходит|работает|делают|почистить|"
    r"установить|заправить|отремонтировать)|можно\s+ли)\b|"
    r"(?:хочу|хотел(?:а)?|нужно)\s+узнать|"
    r"(?:расскажите|подскажите|объясните))",
    re.IGNORECASE,
)
WORKING_HOURS_PATTERN = re.compile(
    r"(?:\bработа(?:ете|ем)\b.*\b(?:пятниц\w*|суббот\w*|"
    r"воскресень\w*)\b|\bграфик\w*\s+работ\w*\b|"
    r"\b(?:какое|укажите|подскажите)\b.*\bрабоч\w*\s+(?:время|часы)\b)",
    re.IGNORECASE,
)


def is_silent_post_lead_message(message: str) -> bool:
    """Определяет реплику, на которую после лида отвечать не нужно."""
    normalized_message = " ".join(message.split())
    return bool(
        THANKS_PATTERN.fullmatch(normalized_message)
        or FAREWELL_PATTERN.fullmatch(normalized_message)
    )


def should_prioritize_business_answer(message: str) -> bool:
    """Определяет вопрос, на который нужно ответить раньше state machine."""
    normalized_message = " ".join(message.split())
    return bool(
        BUSINESS_QUESTION_PATTERN.search(normalized_message)
        or (
            "?" in normalized_message
            and not STATUS_PATTERN.search(normalized_message)
        )
    )


def get_conversation_response(
    message: str,
    lead_created: bool = False,
    customer_name: str | None = None,
    lead_status: str | None = None,
) -> str | None:
    """Возвращает детерминированный ответ для служебных реплик."""
    normalized_message = " ".join(message.split())
    greeting_name = f", {customer_name}" if customer_name else ""

    if lead_created and STATUS_PATTERN.search(normalized_message):
        if lead_status == "new":
            return (
                "Ваша заявка принята и ожидает обработки менеджером. "
                "Повторно оставлять данные не нужно."
            )
        return (
            f"Текущий статус вашей заявки: {lead_status or 'принята'}. "
            "Повторно оставлять данные не нужно."
        )

    if GREETING_PATTERN.fullmatch(normalized_message):
        return f"Здравствуйте{greeting_name}! Чем могу помочь?"

    if WELLBEING_PATTERN.fullmatch(normalized_message):
        return "Спасибо, все хорошо. Чем могу помочь?"

    if IDENTITY_PATTERN.fullmatch(normalized_message):
        return (
            "Я AI-консультант компании. Могу рассказать об услугах, "
            "ценах и помочь оформить заявку."
        )

    if WORKING_HOURS_PATTERN.search(normalized_message):
        return WORKING_HOURS_TEXT

    if THANKS_PATTERN.fullmatch(normalized_message):
        return "Пожалуйста! Задайте еще один вопрос, если потребуется помощь."

    if FAREWELL_PATTERN.fullmatch(normalized_message):
        if lead_created:
            return None
        return "До свидания! Будем рады помочь снова."

    if VAGUE_PATTERN.fullmatch(normalized_message):
        if lead_created:
            return (
                "Уточните, пожалуйста, что именно вы хотите узнать по уже "
                "оформленной заявке или по обслуживанию кондиционера."
            )
        return (
            "Пожалуйста, уточните вопрос. Например, спросите об услугах, "
            "стоимости, графике работы, контактах или оформлении заявки."
        )

    return None
