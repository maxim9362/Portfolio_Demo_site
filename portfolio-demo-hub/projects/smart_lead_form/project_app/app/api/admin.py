# Exposes admin login and credential settings endpoints.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.admin_user import AdminUser
from app.schemas.admin import (
    AdminCredentialsUpdateRequest,
    AdminCredentialsUpdateResponse,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminMeResponse,
)
from app.services.admin_auth_service import authenticate_admin, create_access_token, update_admin_credentials

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/login", response_model=AdminLoginResponse)
def login_admin(payload: AdminLoginRequest, db: Session = Depends(get_db)) -> dict:
    client_id = payload.client_id or settings.default_client_id
    admin_user = authenticate_admin(db, client_id, payload.username, payload.password)
    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )

    return {
        "access_token": create_access_token(admin_user),
        "token_type": "bearer",
        "client_id": admin_user.client_id,
        "username": admin_user.username,
    }


@router.get("/me", response_model=AdminMeResponse)
def get_admin_profile(admin_user: AdminUser = Depends(get_current_admin)) -> dict:
    return {
        "client_id": admin_user.client_id,
        "username": admin_user.username,
    }


@router.put("/credentials", response_model=AdminCredentialsUpdateResponse)
def update_credentials(
    payload: AdminCredentialsUpdateRequest,
    db: Session = Depends(get_db),
    admin_user: AdminUser = Depends(get_current_admin),
) -> dict:
    if payload.client_id != admin_user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нельзя менять настройки другого клиента",
        )

    try:
        updated_admin = update_admin_credentials(
            db,
            admin_user,
            current_password=payload.current_password,
            new_username=payload.new_username,
            new_password=payload.new_password,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Текущий пароль указан неверно",
        ) from exc

    return {
        "status": "updated",
        "client_id": updated_admin.client_id,
        "username": updated_admin.username,
    }
