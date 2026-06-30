# Этот файл содержит SSE-маршрут потокового AI-чата.

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database.db import SessionLocal
from app.llm.client import (
    LLMClient,
    LLMConfigurationError,
    LLMResponseError,
)
from app.rag.embeddings import EmbeddingError
from app.rag.retriever import KnowledgeIndexError
from app.schemas.chat import ChatRequest
from app.services.chat_service import stream_chat_answer


router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/chat")
async def chat(
    payload: ChatRequest,
) -> StreamingResponse:
    """Принимает сообщение пользователя и возвращает поток SSE."""
    try:
        llm_client = LLMClient(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            fallback_model=settings.gemini_fallback_model,
        )
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    db = SessionLocal()
    try:
        answer_stream = stream_chat_answer(
            db=db,
            llm_client=llm_client,
            session_id=payload.session_id,
            user_message=payload.message,
        )
    except SQLAlchemyError as exc:
        db.rollback()
        db.close()
        logger.exception("Не удалось подключиться к базе данных")
        raise HTTPException(
            status_code=503,
            detail=(
                "База данных недоступна. Проверьте PostgreSQL и DATABASE_URL."
            ),
        ) from exc
    except (EmbeddingError, KnowledgeIndexError) as exc:
        db.close()
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return StreamingResponse(
        _as_sse(answer_stream, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _as_sse(
    answer_stream: AsyncIterator[str],
    db: Session,
) -> AsyncIterator[str]:
    """Преобразует фрагменты ответа сервиса в события SSE."""
    try:
        async for chunk in answer_stream:
            yield _sse_event("token", {"text": chunk})
        yield _sse_event("done", {})
    except LLMResponseError as exc:
        logger.warning("Gemini не смог завершить генерацию: %s", exc)
        yield _sse_event("error", {"message": str(exc)})
    except Exception:
        logger.exception("Ошибка потоковой генерации ответа")
        yield _sse_event(
            "error",
            {"message": "Не удалось получить ответ AI. Попробуйте еще раз."},
        )
    finally:
        db.close()


def _sse_event(event: str, data: dict[str, str]) -> str:
    """Формирует одно корректно сериализованное событие SSE."""
    serialized_data = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {serialized_data}\n\n"
