"""FastAPI entrypoint for Portfolio Demo Hub.

This module creates the Hub application, connects public pages, JSON APIs,
protected admin routes, static assets, database table creation, and shared
HTML/JSON error handling.
"""

import logging
import hashlib

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.db import models  # noqa: F401
from app.db.database import Base, SessionLocal, engine
from app.routes import admin, api, pages
from app.services.analytics import bot_info_from_request, record_event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Portfolio Demo Hub")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def on_startup() -> None:
    """Validate startup settings, create Hub tables, and print local links."""
    settings = get_settings()
    if settings.app_env.lower() == "production" and settings.admin_password == "change_me":
        raise RuntimeError("ADMIN_PASSWORD must be changed in production")

    Base.metadata.create_all(bind=engine)
    ensure_runtime_columns()
    logger.info(
        "\n"
        "============================================================\n"
        "Portfolio Demo Hub started\n"
        "\n"
        "Main site:\n"
        "http://localhost/\n"
        "\n"
        "Main admin:\n"
        "http://localhost/admin\n"
        "\n"
        "Admin Basic Auth:\n"
        "username: %s\n"
        "password: configured via ADMIN_PASSWORD\n"
        "============================================================"
        "\n",
        settings.admin_username,
    )


@app.get("/health")
def health() -> dict[str, str]:
    """Small health endpoint for Docker, nginx, and quick browser checks."""
    return {"status": "ok"}


@app.middleware("http")
async def track_bot_page_views(request: Request, call_next):
    """Track crawler page loads separately when bots do not execute analytics.js."""
    response = await call_next(request)
    is_bot, bot_name = bot_info_from_request(request)
    should_track = (
        is_bot
        and request.method == "GET"
        and response.status_code < 400
        and _is_public_html_path(request.url.path)
    )
    if should_track:
        bot_session_id = _bot_session_id(request, bot_name)
        db = SessionLocal()
        try:
            record_event(
                db,
                "page_view",
                session_id=bot_session_id,
                page_url=str(request.url),
                metadata={"server_side": True, "bot_name": bot_name},
                request=request,
            )
            db.commit()
        finally:
            db.close()
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Return a branded HTML 404 for browsers and JSON errors for API calls."""
    if exc.status_code == 404 and "text/html" in request.headers.get("accept", ""):
        return templates.TemplateResponse(
            "error_404.html",
            pages.public_context(
                request.url.path,
                request=request,
                detail=exc.detail,
                robots_noindex=True,
            ),
            status_code=404,
        )
    return JSONResponse(
        {"detail": exc.detail},
        status_code=exc.status_code,
        headers=getattr(exc, "headers", None),
    )


# Routers are kept separate by responsibility: public pages, API endpoints, admin UI.
app.include_router(pages.router)
app.include_router(api.router)
app.include_router(admin.router)


def ensure_runtime_columns() -> None:
    """Add lightweight columns that create_all cannot add to existing tables."""
    statements = [
        "ALTER TABLE contact_leads ADD COLUMN IF NOT EXISTS interest VARCHAR(120)",
        "ALTER TABLE contact_leads ADD COLUMN IF NOT EXISTS project_status VARCHAR(120)",
        "ALTER TABLE visitor_sessions ADD COLUMN IF NOT EXISTS is_bot BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE visitor_sessions ADD COLUMN IF NOT EXISTS bot_name VARCHAR(120)",
        "ALTER TABLE visitor_sessions ADD COLUMN IF NOT EXISTS traffic_type VARCHAR(40) NOT NULL DEFAULT 'human'",
        "ALTER TABLE analytics_events ADD COLUMN IF NOT EXISTS is_bot BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE analytics_events ADD COLUMN IF NOT EXISTS bot_name VARCHAR(120)",
    ]
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def _is_public_html_path(path: str) -> bool:
    """Return true for public pages where bot visits are useful analytics."""
    ignored_prefixes = ("/static", "/api", "/admin", "/health", "/project-assets", "/favicon")
    return not path.startswith(ignored_prefixes)


def _bot_session_id(request: Request, bot_name: str | None) -> str:
    """Create a stable daily session id for one bot/IP/User-Agent combination."""
    ip = request.client.host if request.client else ""
    user_agent = request.headers.get("user-agent", "")
    day = datetime_key()
    raw = f"{day}|{ip}|{user_agent}|{bot_name or ''}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"bot_{digest[:32]}"


def datetime_key() -> str:
    """Return a UTC date key for grouping bot requests into daily sessions."""
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y%m%d")
