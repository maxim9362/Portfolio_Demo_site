# Этот файл содержит защищенные HTML-маршруты административной панели.

from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response,
)
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.admin_credential import AdminCredential
from app.repositories.admin_repository import get_admin
from app.repositories.lead_repository import (
    count_new_leads,
    delete_lead,
    get_latest_lead,
    get_lead_by_id,
    list_leads,
    update_lead_status,
)
from app.repositories.message_repository import get_latest_messages
from app.services.admin_presenter import STATUS_LABELS, present_lead
from app.services.admin_security import get_csrf_token, validate_csrf_token
from app.services.admin_service import (
    authenticate_admin,
    change_admin_credentials,
)


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter(prefix="/admin", tags=["admin"])
ALLOWED_STATUSES = frozenset(STATUS_LABELS)


@router.get("", include_in_schema=False)
async def admin_index(
    request: Request,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Перенаправляет на вход или список заявок."""
    destination = (
        "/admin/leads"
        if _authenticated_admin(request, db) is not None
        else "/admin/login"
    )
    return RedirectResponse(destination, status_code=303)


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Показывает форму входа или открывает заявки авторизованному admin."""
    if _authenticated_admin(request, db) is not None:
        return RedirectResponse("/admin/leads", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context=_template_context(request),
    )


@router.post("/login")
async def login(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Проверяет учетные данные и создает cookie-сессию."""
    form = await request.form()
    if not validate_csrf_token(request, str(form.get("csrf_token", ""))):
        return _csrf_error(request)

    admin = authenticate_admin(
        db=db,
        username=str(form.get("username", "")),
        password=str(form.get("password", "")),
    )
    if admin is None:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context=_template_context(
                request,
                error="Неверный логин или пароль",
                username=str(form.get("username", "")),
            ),
            status_code=400,
        )

    request.session.clear()
    request.session["admin_id"] = admin.id
    request.session["csrf_token"] = get_csrf_token(request)
    return RedirectResponse("/admin/leads", status_code=303)


@router.post("/logout")
async def logout(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Завершает административную cookie-сессию."""
    unauthorized = _login_redirect_if_needed(request, db)
    if unauthorized:
        return unauthorized
    form = await request.form()
    if not validate_csrf_token(request, str(form.get("csrf_token", ""))):
        return _csrf_error(request)
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=303)


@router.get("/leads", response_class=HTMLResponse)
async def leads_page(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Показывает таблицу заявок, отсортированную от новых к старым."""
    unauthorized = _login_redirect_if_needed(request, db)
    if unauthorized:
        return unauthorized
    leads = [present_lead(lead) for lead in list_leads(db)]
    return templates.TemplateResponse(
        request=request,
        name="leads.html",
        context=_template_context(
            request,
            leads=leads,
            new_count=count_new_leads(db),
        ),
    )


@router.get("/leads/latest-info")
async def latest_lead_info(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Возвращает данные для периодической проверки новых заявок."""
    unauthorized = _login_redirect_if_needed(request, db)
    if unauthorized:
        return unauthorized
    latest = get_latest_lead(db)
    return JSONResponse(
        {
            "latest_lead_id": latest.id if latest else None,
            "latest_created_at": (
                latest.created_at.isoformat() if latest else None
            ),
            "new_count": count_new_leads(db),
        }
    )


@router.get("/leads/{lead_id}", response_class=HTMLResponse)
async def lead_detail_page(
    lead_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Показывает заявку и последние сообщения ее диалога."""
    unauthorized = _login_redirect_if_needed(request, db)
    if unauthorized:
        return unauthorized
    lead = get_lead_by_id(db, lead_id)
    if lead is None:
        return _not_found(request, "Заявка не найдена")
    messages = get_latest_messages(db, lead.session_id, limit=12)
    return templates.TemplateResponse(
        request=request,
        name="lead_detail.html",
        context=_template_context(
            request,
            lead=present_lead(lead),
            messages=messages,
            statuses=STATUS_LABELS,
        ),
    )


@router.post("/leads/{lead_id}/status")
async def change_lead_status(
    lead_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Проверяет и сохраняет новый статус заявки."""
    unauthorized = _login_redirect_if_needed(request, db)
    if unauthorized:
        return unauthorized
    form = await request.form()
    if not validate_csrf_token(request, str(form.get("csrf_token", ""))):
        return _csrf_error(request)
    status = str(form.get("status", ""))
    if status not in ALLOWED_STATUSES:
        return _not_found(request, "Недопустимый статус", status_code=400)
    lead = get_lead_by_id(db, lead_id)
    if lead is None:
        return _not_found(request, "Заявка не найдена")
    update_lead_status(db, lead, status)
    _set_flash(request, "Статус заявки обновлен")
    return RedirectResponse(f"/admin/leads/{lead_id}", status_code=303)


@router.post("/leads/{lead_id}/delete")
async def remove_lead(
    lead_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Удаляет заявку и связанный диалог после защищенного POST-запроса."""
    unauthorized = _login_redirect_if_needed(request, db)
    if unauthorized:
        return unauthorized
    form = await request.form()
    if not validate_csrf_token(request, str(form.get("csrf_token", ""))):
        return _csrf_error(request)
    lead = get_lead_by_id(db, lead_id)
    if lead is None:
        return _not_found(request, "Заявка не найдена")
    delete_lead(db, lead)
    _set_flash(request, "Заявка и связанный диалог удалены")
    return RedirectResponse("/admin/leads", status_code=303)


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Показывает форму смены логина и пароля."""
    admin = _authenticated_admin(request, db)
    if admin is None:
        return RedirectResponse("/admin/login", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context=_template_context(request, admin=admin),
    )


@router.post("/settings")
async def save_settings(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Обновляет учетные данные после проверки текущего пароля."""
    admin = _authenticated_admin(request, db)
    if admin is None:
        return RedirectResponse("/admin/login", status_code=303)
    form = await request.form()
    if not validate_csrf_token(request, str(form.get("csrf_token", ""))):
        return _csrf_error(request)

    try:
        updated, password_changed = change_admin_credentials(
            db=db,
            admin=admin,
            current_password=str(form.get("current_password", "")),
            new_username=str(form.get("new_username", "")),
            new_password=str(form.get("new_password", "")),
            new_password_confirm=str(form.get("new_password_confirm", "")),
        )
    except ValueError as exc:
        return templates.TemplateResponse(
            request=request,
            name="settings.html",
            context=_template_context(request, admin=admin, error=str(exc)),
            status_code=400,
        )

    if password_changed:
        request.session.clear()
        _set_flash(request, "Пароль обновлен. Войдите заново.")
        return RedirectResponse("/admin/login", status_code=303)

    request.session["admin_id"] = updated.id
    _set_flash(request, "Данные доступа обновлены")
    return RedirectResponse("/admin/settings", status_code=303)


def _authenticated_admin(
    request: Request,
    db: Session,
) -> AdminCredential | None:
    """Проверяет административный идентификатор в подписанной сессии."""
    admin_id = request.session.get("admin_id")
    if not isinstance(admin_id, int):
        return None
    admin = get_admin(db)
    if admin is None or admin.id != admin_id:
        return None
    return admin


def _login_redirect_if_needed(
    request: Request,
    db: Session,
) -> RedirectResponse | None:
    """Возвращает редирект на вход для неавторизованного запроса."""
    if _authenticated_admin(request, db) is None:
        return RedirectResponse("/admin/login", status_code=303)
    return None


def _template_context(request: Request, **values: Any) -> dict[str, Any]:
    """Добавляет общие данные, flash и CSRF-токен в контекст шаблона."""
    return {
        "csrf_token": get_csrf_token(request),
        "flash": request.session.pop("flash", None),
        "current_year": datetime.now().year,
        "is_authenticated": isinstance(request.session.get("admin_id"), int),
        **values,
    }


def _set_flash(request: Request, message: str) -> None:
    """Сохраняет одно сообщение для следующей HTML-страницы."""
    request.session["flash"] = message


def _csrf_error(request: Request) -> HTMLResponse:
    """Показывает понятную ошибку при недействительном CSRF-токене."""
    return _not_found(
        request,
        "Сессия формы устарела. Обновите страницу и повторите действие.",
        status_code=403,
    )


def _not_found(
    request: Request,
    message: str,
    status_code: int = 404,
) -> HTMLResponse:
    """Отображает общую административную страницу ошибки."""
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context=_template_context(request, error=message),
        status_code=status_code,
    )
