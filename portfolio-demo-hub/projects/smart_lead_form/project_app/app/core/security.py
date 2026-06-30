# Provides authentication helpers for administrative endpoints.

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.services.admin_auth_service import get_admin_by_token


def verify_admin_api_key(
    x_admin_api_key: str | None = Header(default=None, alias="X-Admin-Api-Key"),
) -> bool:
    """Verify the admin API key from the X-Admin-Api-Key header."""
    if not settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin API key is not configured",
        )

    if x_admin_api_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin API key",
        )

    return True


def get_current_admin(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_admin_api_key: str | None = Header(default=None, alias="X-Admin-Api-Key"),
    db: Session = Depends(get_db),
) -> AdminUser:
    """Authorize admin requests by Bearer token, with legacy API key fallback."""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        admin_user = get_admin_by_token(db, token)
        if admin_user:
            return admin_user

    if settings.admin_api_key and x_admin_api_key == settings.admin_api_key:
        from app.services.admin_auth_service import ensure_default_admin_user

        return ensure_default_admin_user(db)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Admin authentication required",
    )
