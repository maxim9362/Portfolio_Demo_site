# Этот файл создает FastAPI-приложение и подключает API и статический интерфейс.

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
import asyncio
import logging
import secrets

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.admin.router import router as admin_router
from app.api.router import api_router
from app.config import settings
from app.database.initializer import initialize_database
from app.services.data_retention_service import (
    delete_expired_leads,
    retention_cleanup_loop,
    stop_retention_task,
)
from app.widget.router import router as widget_router


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
logger = logging.getLogger(__name__)
startup_logger = logging.getLogger("uvicorn.error")


def _admin_session_secret() -> str:
    """Возвращает production-секрет или временный development-секрет."""
    if settings.admin_session_secret.strip():
        return settings.admin_session_secret
    logger.warning(
        "ADMIN_SESSION_SECRET не задан: используется временный development-secret."
    )
    return secrets.token_urlsafe(48)


ADMIN_SESSION_SECRET = _admin_session_secret()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Подготавливает общую базу чата и админки при запуске приложения."""
    admin = initialize_database()
    deleted_count = await asyncio.to_thread(delete_expired_leads)
    retention_task = asyncio.create_task(retention_cleanup_loop())
    startup_logger.info(
        "\n"
        "Чат:     http://127.0.0.1:8000\n"
        "Админка: http://127.0.0.1:8000/admin\n"
        "Администратор: %s\n"
        "Хранение заявок: %s дней; удалено при запуске: %s",
        admin.username,
        settings.lead_retention_days,
        deleted_count,
    )
    try:
        yield
    finally:
        await stop_retention_task(retention_task)


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=ADMIN_SESSION_SECRET,
    session_cookie="ai_consultant_admin",
    max_age=60 * 60 * 12,
    same_site="lax",
    https_only=settings.admin_cookie_secure,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.include_router(api_router)
app.include_router(widget_router)
app.include_router(admin_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
async def health() -> dict[str, str]:
    """Сообщает, что HTTP-приложение запущено."""
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    """Отдает главную HTML-страницу чата."""
    return FileResponse(STATIC_DIR / "index.html")
