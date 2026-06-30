# Этот файл проверяет рабочее время компании и пожелания клиента по времени связи.

from datetime import datetime
import re
from zoneinfo import ZoneInfo


ISRAEL_TIMEZONE = ZoneInfo("Asia/Jerusalem")
WORKING_HOURS_TEXT = (
    "Рабочее время компании: воскресенье–четверг 09:00–18:00, "
    "пятница 09:00–13:00, суббота — выходной."
)


def is_company_open(moment: datetime | None = None) -> bool:
    """Проверяет, работает ли компания в указанный момент."""
    current = moment or datetime.now(ISRAEL_TIMEZONE)
    if current.tzinfo is None:
        current = current.replace(tzinfo=ISRAEL_TIMEZONE)
    else:
        current = current.astimezone(ISRAEL_TIMEZONE)

    weekday = current.weekday()
    minutes = current.hour * 60 + current.minute
    if weekday == 5:
        return False
    if weekday == 4:
        return 9 * 60 <= minutes < 13 * 60
    return 9 * 60 <= minutes < 18 * 60


WEEKDAY_ALIASES = {
    "понедельник": 0,
    "вторник": 1,
    "среду": 2,
    "четверг": 3,
    "пятницу": 4,
    "субботу": 5,
    "воскресенье": 6,
}


def preferred_time_is_outside_hours(
    preferred_time: str | None,
    moment: datetime | None = None,
) -> bool:
    """Определяет, выходит ли пожелание за рабочие часы."""
    if not preferred_time:
        return False

    normalized = preferred_time.casefold().replace("ё", "е")
    if "вечер" in normalized or "после работы" in normalized:
        return True

    current = _israel_datetime(moment)
    target_weekday = _target_weekday(normalized, current.weekday())
    if target_weekday == 5:
        return True

    times = [
        (int(hour), int(minute or 0))
        for hour, minute in re.findall(
            r"(?<!\d)([01]?\d|2[0-3])(?:[:.-]([0-5]\d))?(?!\d)",
            normalized,
        )
    ]
    if target_weekday == 4 and any(
        hour >= 13
        for hour, _ in times
    ):
        return True
    return any(
        hour >= 18 or hour < 9 or minute > 59
        for hour, minute in times
    )


def working_hours_notice(
    preferred_time: str | None,
    moment: datetime | None = None,
) -> str:
    """Возвращает предупреждение для нерабочего времени."""
    if preferred_time_is_outside_hours(preferred_time, moment):
        return (
            "В это время компания обычно не работает, но мы передадим ваше "
            "пожелание. Менеджер свяжется с вами в ближайшее доступное "
            f"рабочее время. {WORKING_HOURS_TEXT}"
        )
    if not is_company_open(moment):
        return (
            "Сейчас компания не работает. Заявка принята, и менеджер "
            "свяжется с вами в ближайший рабочий день в указанное вами время. "
            f"{WORKING_HOURS_TEXT}"
        )
    return ""


def _israel_datetime(moment: datetime | None) -> datetime:
    """Переводит момент в часовой пояс Израиля."""
    current = moment or datetime.now(ISRAEL_TIMEZONE)
    if current.tzinfo is None:
        return current.replace(tzinfo=ISRAEL_TIMEZONE)
    return current.astimezone(ISRAEL_TIMEZONE)


def _target_weekday(normalized_time: str, current_weekday: int) -> int | None:
    """Определяет день недели из пожелания клиента."""
    if "сегодня" in normalized_time:
        return current_weekday
    if "завтра" in normalized_time:
        return (current_weekday + 1) % 7
    for alias, weekday in WEEKDAY_ALIASES.items():
        if alias in normalized_time:
            return weekday
    return None
