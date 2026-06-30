# Этот файл извлекает контактные данные и интересующую услугу из сообщений пользователя.

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
import re
from zoneinfo import ZoneInfo


EMAIL_PATTERN = re.compile(
    r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?![\w.-])",
    re.IGNORECASE,
)
PHONE_CANDIDATE_PATTERN = re.compile(
    r"(?<!\d)(?:\+972|00972|0)?[\s(.-]*(?:\d[\s()\-]*){8,10}(?!\d)"
)
NAME_PATTERNS = (
    re.compile(
        r"(?:меня\s+зовут|мо[её]\s+имя|имя)\s*[:\-]?\s*"
        r"([А-ЯЁA-Z][а-яёa-z]+(?:[\s-][А-ЯЁA-Z][а-яёa-z]+){0,2})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|[.!?]\s+)([А-ЯЁA-Z][а-яёa-z]{1,30})"
        r"(?=\s*[,;:]?\s*(?:\+972|00972|0)?[\s(.-]*(?:\d[\s()\-]*){8,10})",
        re.IGNORECASE,
    ),
)
STANDALONE_NAME_PATTERN = re.compile(
    r"^[А-ЯЁA-Z][а-яёa-z]{1,30}$",
    re.IGNORECASE,
)
NON_NAME_WORDS = {
    "да",
    "нет",
    "хорошо",
    "ладно",
    "ок",
    "окей",
    "можно",
    "хочу",
    "утром",
    "вечером",
    "сегодня",
    "завтра",
    "воскресенье",
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "привет",
    "здравствуйте",
    "спасибо",
    "помогите",
    "консультация",
    "ремонт",
    "диагностика",
    "установка",
    "сборка",
    "ашдод",
    "ашкелон",
    "явне",
    "ган-явне",
    "кирьят-малахи",
}
SERVICE_KEYWORDS = {
    "диагностика кондиционера": (
        "диагност",
        "осмотр",
        "выезд мастера",
    ),
    "ремонт кондиционера": (
        "ремонт",
        "почин",
        "сломал",
        "не охлаждает",
        "не греет",
        "не включается",
        "течет",
        "течёт",
        "шумит",
        "ошибка",
    ),
    "установка кондиционера": (
        "установ",
        "монтаж",
        "поставить кондиционер",
    ),
    "чистка кондиционера": (
        "чистк",
        "почист",
        "очист",
        "помыть",
        "помыть кондиционер",
        "мойк",
        "плесень",
        "запах",
    ),
    "заправка газа": (
        "заправ",
        "газ",
        "фреон",
        "хладагент",
    ),
    "обслуживание кондиционера": (
        "обслужив",
        "техобслуж",
        "планов",
    ),
    "демонтаж кондиционера": (
        "демонтаж",
        "снять кондиционер",
        "перенести кондиционер",
    ),
    "консультация": (
        "консультац",
        "проконсульт",
        "вопрос специалист",
    ),
}
PROBLEM_PATTERN = re.compile(
    r"(?:не\s+охлаждает|не\s+греет|не\s+включается|не\s+работает|"
    r"течет|течёт|капает|шумит|вибрирует|пахнет|запах|"
    r"выбивает|ошибк\w*|обмерз\w*|лед|лёд|"
    r"слаб\w*\s+(?:поток(?:\s+воздуха)?|дует)|плохо\s+дует)",
    re.IGNORECASE,
)
CITY_ALIASES = {
    "ашдод": "Ашдод",
    "ашкелон": "Ашкелон",
    "ган явне": "Ган-Явне",
    "ган-явне": "Ган-Явне",
    "явне": "Явне",
    "кириат малахи": "Кирьят-Малахи",
    "кириат-малахи": "Кирьят-Малахи",
    "кирьят малахи": "Кирьят-Малахи",
    "кирьят-малахи": "Кирьят-Малахи",
}
ISRAEL_TIMEZONE = ZoneInfo("Asia/Jerusalem")
TIME_PART = r"(?:[01]?\d|2[0-3])(?:[:.-][0-5]\d)"
HOUR_PART = r"(?:[01]?\d|2[0-3])"
INCOMPLETE_TIME_PATTERN = re.compile(
    r"^\s*(?:[01]?\d|2[0-3])[:.-]\d\s*$"
)
BARE_TIME_PATTERN = re.compile(
    rf"^\s*(?P<hour>[01]?\d|2[0-3])[:.-](?P<minute>[0-5]\d)\s*$"
)
DAY_WITH_TIME_PATTERN = re.compile(
    rf"^\s*(?:(?P<day_before>сегодня|завтра)\s+(?:в\s+)?"
    rf"(?P<time_after>{TIME_PART})|(?P<time_before>{TIME_PART})\s+"
    rf"(?P<day_after>сегодня|завтра))\s*$",
    re.IGNORECASE,
)
CONTACT_TIME_PATTERNS = (
    re.compile(
        r"\b(?:сегодня|завтра)(?:\s+(?:утром|днем|днём|вечером|"
        rf"(?:в|после|до)\s+{TIME_PART}))?\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\bс\s+{HOUR_PART}(?:[:.-][0-5]\d)?\s+до\s+"
        rf"{HOUR_PART}(?:[:.-][0-5]\d)?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:утром|вечером|после\s+обеда|в\s+любое\s+время|"
        r"в\s+рабочее\s+время|после\s+работы)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:в|во)\s+(?:воскресенье|понедельник|вторник|среду|"
        r"четверг|пятницу|субботу)(?:\s+(?:утром|вечером|"
        rf"(?:в|после|до)\s+{TIME_PART}))?\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?:после|до|к|в)\s+{TIME_PART}\b",
        re.IGNORECASE,
    ),
)


@dataclass(frozen=True, slots=True)
class ExtractedLead:
    """Содержит контактные данные, распознанные в сообщениях."""
    name: str | None
    phone: str | None
    email: str | None
    service: str | None
    preferred_contact_time: str | None


def extract_lead_data(messages: Iterable[str]) -> ExtractedLead:
    """Собирает последние известные поля лида из сообщений."""
    texts = [message.strip() for message in messages if message.strip()]
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    service: str | None = None
    preferred_contact_time: str | None = None

    for text in reversed(texts):
        if name is None:
            name = _extract_name(text) or _extract_standalone_name(text)
        if phone is None:
            phone = extract_phone(text)
        if email is None:
            email_match = EMAIL_PATTERN.search(text)
            if email_match:
                email = email_match.group(0).lower()
        if service is None:
            service = _extract_service(text)
        if preferred_contact_time is None:
            preferred_contact_time = extract_preferred_contact_time(text)

    return ExtractedLead(
        name=name,
        phone=phone,
        email=email,
        service=service,
        preferred_contact_time=preferred_contact_time,
    )


def extract_name(text: str) -> str | None:
    """Извлекает явно указанное имя."""
    return _extract_name(text)


def extract_phone(text: str) -> str | None:
    """Находит и нормализует израильский мобильный номер."""
    for match in PHONE_CANDIDATE_PATTERN.finditer(text):
        normalized_phone = _normalize_phone(match.group(0))
        if normalized_phone is not None:
            return normalized_phone
    return None


def extract_email(text: str) -> str | None:
    """Извлекает email-адрес из текста."""
    match = EMAIL_PATTERN.search(text)
    return match.group(0).lower() if match else None


def extract_service(text: str) -> str | None:
    """Определяет интересующую услугу по ключевым словам."""
    return _extract_service(text)


def extract_problem(text: str) -> str | None:
    """Возвращает текст при наличии симптома неисправности."""
    match = PROBLEM_PATTERN.search(text)
    return match.group(0).strip() if match else None


def extract_city(text: str) -> str | None:
    """Распознает город из зоны обслуживания."""
    normalized_text = normalize_air_conditioner_text(text)
    for alias, city in CITY_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", normalized_text):
            return city
    return None


def extract_preferred_contact_time(
    text: str,
    moment: datetime | None = None,
) -> str | None:
    """Извлекает удобный день или время обратной связи."""
    normalized_text = " ".join(text.strip().split())
    day_with_time_match = DAY_WITH_TIME_PATTERN.fullmatch(normalized_text)
    if day_with_time_match:
        day = (
            day_with_time_match.group("day_before")
            or day_with_time_match.group("day_after")
        ).casefold()
        clock = (
            day_with_time_match.group("time_after")
            or day_with_time_match.group("time_before")
        )
        return f"{day} в {_normalize_clock(clock)}"

    bare_time_match = BARE_TIME_PATTERN.fullmatch(normalized_text)
    if bare_time_match:
        hour = int(bare_time_match.group("hour"))
        minute = int(bare_time_match.group("minute"))
        current = _israel_datetime(moment)
        day = (
            "сегодня"
            if (hour, minute) >= (current.hour, current.minute)
            else "завтра"
        )
        return f"{day} в {hour:02d}:{minute:02d}"

    for pattern in CONTACT_TIME_PATTERNS:
        match = pattern.search(normalized_text)
        if match:
            return _normalize_time_separators(match.group(0))
    return None


def is_incomplete_contact_time(text: str) -> bool:
    """Проверяет неполную запись времени вроде 13:3."""
    return bool(INCOMPLETE_TIME_PATTERN.fullmatch(text))


def _israel_datetime(moment: datetime | None) -> datetime:
    """Возвращает момент в часовом поясе Израиля."""
    current = moment or datetime.now(ISRAEL_TIMEZONE)
    if current.tzinfo is None:
        return current.replace(tzinfo=ISRAEL_TIMEZONE)
    return current.astimezone(ISRAEL_TIMEZONE)


def _normalize_time_separators(text: str) -> str:
    """Приводит разделитель времени к двоеточию."""
    return re.sub(
        r"(?P<hour>\b(?:[01]?\d|2[0-3]))[.-](?P<minute>[0-5]\d\b)",
        r"\g<hour>:\g<minute>",
        text,
    )


def _normalize_clock(value: str) -> str:
    """Приводит отдельное время к формату ЧЧ:ММ."""
    hour, minute = re.split(r"[:.-]", value)
    return f"{int(hour):02d}:{int(minute):02d}"


def _extract_name(text: str) -> str | None:
    """Ищет имя в явной фразе или рядом с телефоном."""
    for pattern in NAME_PATTERNS:
        match = pattern.search(text)
        if match:
            return " ".join(part.capitalize() for part in match.group(1).split())
    return None


def _extract_standalone_name(text: str) -> str | None:
    """Проверяет, может ли одиночное слово быть именем."""
    normalized_text = text.strip()
    if not STANDALONE_NAME_PATTERN.fullmatch(normalized_text):
        return None
    if normalized_text.casefold() in NON_NAME_WORDS:
        return None
    return normalized_text.capitalize()


def _normalize_phone(phone: str) -> str | None:
    """Приводит номер к международному формату +972."""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("00972"):
        digits = digits[2:]
    if digits.startswith("972"):
        national_number = digits[3:]
    elif digits.startswith("0"):
        national_number = digits[1:]
    else:
        return None

    if not re.fullmatch(r"5[0-58]\d{7}", national_number):
        return None
    return f"+972{national_number}"


def _extract_service(text: str) -> str | None:
    """Сопоставляет текст с каталогом услуг."""
    normalized_text = normalize_air_conditioner_text(text)
    for service, keywords in SERVICE_KEYWORDS.items():
        if any(keyword in normalized_text for keyword in keywords):
            return service
    return None


def normalize_air_conditioner_text(text: str) -> str:
    """Нормализует частые варианты слова кондиционер."""
    normalized_text = text.casefold().replace("ё", "е")
    conditioner_pattern = re.compile(
        r"\b(?:кондиционер\w*|кондеционер\w*|кондицеонер\w*|"
        r"кондец(?:ионер\w*)?|кондер\w*|кондей\w*|кондишен\w*)\b",
        re.IGNORECASE,
    )
    return conditioner_pattern.sub("кондиционер", normalized_text)
