# Этот файл автоматически удаляет устаревшие заявки и связанные диалоги.

import asyncio
from contextlib import suppress
from datetime import datetime, timedelta, timezone
import logging

from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database.db import SessionLocal
from app.repositories.lead_repository import delete_leads_created_before


logger = logging.getLogger(__name__)


def delete_expired_leads() -> int:
    """Удаляет заявки старше настроенного срока хранения."""
    cutoff = datetime.now(timezone.utc) - timedelta(
        days=settings.lead_retention_days
    )
    with SessionLocal() as db:
        try:
            deleted_count = delete_leads_created_before(db, cutoff)
        except SQLAlchemyError:
            db.rollback()
            logger.exception("Не удалось удалить устаревшие заявки")
            return 0

    if deleted_count:
        logger.info(
            "Удалено устаревших заявок вместе с диалогами: %s",
            deleted_count,
        )
    return deleted_count


async def retention_cleanup_loop() -> None:
    """Периодически запускает очистку без блокировки event loop."""
    while True:
        await asyncio.sleep(settings.lead_cleanup_interval_seconds)
        await asyncio.to_thread(delete_expired_leads)


async def stop_retention_task(task: asyncio.Task[None]) -> None:
    """Корректно останавливает фоновую очистку при завершении приложения."""
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
