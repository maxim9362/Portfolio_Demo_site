"""FastAPI entrypoint for Portfolio Demo Hub.

This module creates the Hub application, connects public pages, JSON APIs,
protected admin routes, static assets, database table creation, and shared
HTML/JSON error handling.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.db import models  # noqa: F401
from app.db.database import Base, engine
from app.routes import admin, api, pages

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


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Return a branded HTML 404 for browsers and JSON errors for API calls."""
    if exc.status_code == 404 and "text/html" in request.headers.get("accept", ""):
        return templates.TemplateResponse(
            "error_404.html",
            {"request": request, "detail": exc.detail},
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
