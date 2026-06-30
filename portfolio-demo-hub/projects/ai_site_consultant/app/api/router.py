# Этот файл объединяет все API-маршруты приложения под единым префиксом.

from fastapi import APIRouter

from app.api.chat import router as chat_router
from app.api.ingest import router as ingest_router
from app.api.leads import router as leads_router


api_router = APIRouter(prefix="/api")
api_router.include_router(chat_router)
api_router.include_router(leads_router)
api_router.include_router(ingest_router)
