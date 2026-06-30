# Exposes endpoints for creating and listing lead records.

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.admin_user import AdminUser
from app.schemas.lead import (
    LeadCreate,
    LeadCreateResponse,
    LeadDeleteResponse,
    LeadListResponse,
    LeadStatusUpdate,
    LeadStatusUpdateResponse,
    LeadUpdateResponse,
)
from app.services.lead_service import create_lead, delete_lead, list_leads, update_lead, update_lead_status

router = APIRouter(prefix="/api/leads", tags=["leads"])

PHONE_ERROR_DETAIL = "Пожалуйста, укажите израильский номер телефона в формате 05XXXXXXXX или +972XXXXXXXXX."
TIME_ERROR_DETAIL = "Пожалуйста, укажите время в формате ЧЧ:ММ, например: завтра в 12:30."
OFFICE_CLOSED_DETAIL = "В это время офис закрыт. Мы свяжемся с вами завтра в рабочее время или укажите другое удобное время."
SHABBAT_CLOSED_DETAIL = "Сейчас Шабат, офис закрыт. Мы свяжемся с вами на следующий рабочий день или укажите удобное время, например: завтра в 12:30."
RECENT_LEAD_ERROR_DETAIL = "Заявка уже создана, ее можно изменить. Новую заявку можно оформить только через сутки."


@router.post("", response_model=LeadCreateResponse)
def create_lead_endpoint(payload: LeadCreate, db: Session = Depends(get_db)) -> dict:
    try:
        lead = create_lead(db, payload)
    except ValueError as exc:
        if str(exc) == "Invalid Israeli phone number":
            raise HTTPException(status_code=400, detail=PHONE_ERROR_DETAIL) from exc
        if str(exc) == "Invalid contact time":
            raise HTTPException(status_code=400, detail=TIME_ERROR_DETAIL) from exc
        if str(exc) == "Office closed for time":
            raise HTTPException(status_code=400, detail=OFFICE_CLOSED_DETAIL) from exc
        if str(exc) == "Office closed for shabbat":
            raise HTTPException(status_code=400, detail=SHABBAT_CLOSED_DETAIL) from exc
        if str(exc) == "Recent lead already exists":
            raise HTTPException(status_code=409, detail=RECENT_LEAD_ERROR_DETAIL) from exc
        raise

    return {
        "id": lead.id,
        "status": "created",
        "message": "Заявка создана",
    }


@router.get("", response_model=LeadListResponse)
def list_leads_endpoint(
    client_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> dict:
    items, total = list_leads(db, client_id=client_id, limit=limit, offset=offset)
    return {"items": items, "total": total}


@router.put("/{lead_id}", response_model=LeadUpdateResponse)
def update_lead_endpoint(lead_id: int, payload: LeadCreate, db: Session = Depends(get_db)) -> dict:
    try:
        lead = update_lead(db, lead_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Заявка не найдена") from exc
    except ValueError as exc:
        if str(exc) == "Invalid Israeli phone number":
            raise HTTPException(status_code=400, detail=PHONE_ERROR_DETAIL) from exc
        if str(exc) == "Invalid contact time":
            raise HTTPException(status_code=400, detail=TIME_ERROR_DETAIL) from exc
        if str(exc) == "Office closed for time":
            raise HTTPException(status_code=400, detail=OFFICE_CLOSED_DETAIL) from exc
        if str(exc) == "Office closed for shabbat":
            raise HTTPException(status_code=400, detail=SHABBAT_CLOSED_DETAIL) from exc
        raise

    return {
        "id": lead.id,
        "status": "updated",
        "message": "Заявка обновлена",
    }


@router.patch("/{lead_id}/status", response_model=LeadStatusUpdateResponse)
def update_lead_status_endpoint(
    lead_id: int,
    payload: LeadStatusUpdate,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> dict:
    try:
        lead = update_lead_status(db, lead_id=lead_id, status=payload.status)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Заявка не найдена") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Недопустимый статус заявки") from exc

    return {"id": lead.id, "status": lead.status}


@router.delete("/{lead_id}", response_model=LeadDeleteResponse)
def delete_lead_endpoint(
    lead_id: int,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> dict:
    try:
        delete_lead(db, lead_id=lead_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Заявка не найдена") from exc

    return {"id": lead_id, "status": "deleted"}
