# Этот файл отдает автономный JavaScript-виджет для внешних сайтов.

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse


WIDGET_DIR = Path(__file__).resolve().parent
router = APIRouter(prefix="/widget", tags=["widget"])


@router.get("/chat-widget.js", include_in_schema=False)
def chat_widget() -> FileResponse:
    """Отдает JavaScript-файл встраиваемого чат-виджета."""
    return FileResponse(
        WIDGET_DIR / "chat-widget.js",
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=300"},
    )
