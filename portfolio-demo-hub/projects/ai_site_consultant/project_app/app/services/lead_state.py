# Этот файл собирает известные данные заявки из полной истории диалога.

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import re
from typing import Protocol

from app.models.lead import Lead
from app.services.lead_extractor import (
    extract_city,
    extract_lead_data,
    extract_name,
    extract_problem,
    extract_service,
)


class LeadStateMessage(Protocol):
    """Описывает сообщение для восстановления состояния заявки."""
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class LeadState:
    """Содержит поля заявки, восстановленные из PostgreSQL."""
    service: str | None
    problem: str | None
    city: str | None
    name: str | None
    phone: str | None
    email: str | None
    preferred_contact_time: str | None
    lead_created: bool


NAME_ANSWER_PATTERN = re.compile(
    r"^[А-ЯЁA-Z][а-яёa-z]{1,30}"
    r"(?:[\s-][А-ЯЁA-Z][а-яёa-z]{1,30}){0,2}$",
    re.IGNORECASE,
)
NAME_QUESTION_MARKERS = (
    "как к вам обращаться",
    "только ваше имя",
)
NAME_STOP_WORDS = {
    "да",
    "нет",
    "хорошо",
    "ладно",
    "ок",
    "окей",
    "можно",
    "хочу",
}


def build_lead_state(
    messages: Sequence[LeadStateMessage],
    lead: Lead | None = None,
) -> LeadState:
    """Восстанавливает состояние из истории и сохраненного лида."""
    user_messages = [
        message.content.strip()
        for message in messages
        if message.role == "user" and message.content.strip()
    ]
    extracted = extract_lead_data(user_messages)
    problem = _last_extracted(user_messages, extract_problem)
    city = _last_extracted(user_messages, extract_city)
    service = (
        extracted.service
        if extracted.service != "консультация"
        else None
    )

    if lead is not None:
        service = _lead_detail(lead.message, "Услуга") or service
        problem = _lead_detail(lead.message, "Проблема") or problem
        city = _lead_detail(lead.message, "Город") or city

    return LeadState(
        service=service,
        problem=problem,
        city=city,
        name=lead.name if lead and lead.name else _extract_contextual_name(messages),
        phone=lead.phone if lead and lead.phone else extracted.phone,
        email=lead.email if lead and lead.email else extracted.email,
        preferred_contact_time=(
            lead.preferred_contact_time
            if lead and lead.preferred_contact_time
            else extracted.preferred_contact_time
        ),
        lead_created=lead is not None,
    )


def _last_extracted(
    messages: list[str],
    extractor: Callable[[str], str | None],
) -> str | None:
    """Возвращает последнее распознанное значение."""
    for message in reversed(messages):
        value = extractor(message)
        if value:
            return value
    return None


def _lead_detail(message: str | None, label: str) -> str | None:
    """Извлекает подписанное поле из описания лида."""
    if not message:
        return None
    match = re.search(
        rf"(?:^|\n|[.!?]\s+){re.escape(label)}:\s*([^.\n]+)",
        message,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


def _extract_contextual_name(
    messages: Sequence[LeadStateMessage],
) -> str | None:
    """Распознает имя явно или как ответ на вопрос бота."""
    for message in reversed(messages):
        if message.role != "user":
            continue
        explicit_name = extract_name(message.content)
        if explicit_name:
            return explicit_name

    for index in range(len(messages) - 1, 0, -1):
        answer = messages[index]
        prompt = messages[index - 1]
        if answer.role != "user" or prompt.role != "assistant":
            continue
        if not any(
            marker in prompt.content.casefold()
            for marker in NAME_QUESTION_MARKERS
        ):
            continue
        candidate = answer.content.strip()
        if (
            NAME_ANSWER_PATTERN.fullmatch(candidate)
            and candidate.casefold() not in NAME_STOP_WORDS
            and extract_city(candidate) is None
            and extract_service(candidate) is None
        ):
            return " ".join(part.capitalize() for part in candidate.split())
    return None
