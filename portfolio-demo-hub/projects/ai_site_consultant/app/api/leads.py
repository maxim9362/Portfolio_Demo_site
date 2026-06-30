# Этот файл содержит API-маршрут получения списка созданных лидов.

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.repositories.lead_repository import list_leads
from app.schemas.lead import LeadResponse


router = APIRouter(tags=["leads"])


@router.get("/leads", response_model=list[LeadResponse])
def get_leads(db: Session = Depends(get_db)) -> list[LeadResponse]:
    """Возвращает сохраненные заявки в порядке от новых к старым."""
    return [
        LeadResponse.model_validate(lead)
        for lead in list_leads(db)
    ]
