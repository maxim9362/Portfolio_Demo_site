# Этот файл описывает входные данные потокового chat API.

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Проверяет входные данные запроса к AI-чату."""
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=4000)
    demo_session_id: str | None = Field(default=None, max_length=128)
