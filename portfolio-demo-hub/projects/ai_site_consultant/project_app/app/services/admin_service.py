# Этот файл содержит бизнес-логику единственной административной учетной записи.

from sqlalchemy.orm import Session

from app.models.admin_credential import AdminCredential
from app.repositories.admin_repository import (
    create_initial_admin,
    get_admin,
    update_admin_credentials,
)
from app.services.admin_security import hash_password, verify_password


class AdminConfigurationError(RuntimeError):
    """Сообщает о некорректных первичных настройках администратора."""


def ensure_initial_admin(
    db: Session,
    username: str,
    password: str,
) -> AdminCredential:
    """Создает первого администратора, не перезаписывая существующего."""
    existing = get_admin(db)
    if existing is not None:
        return existing

    normalized_username = username.strip()
    if not normalized_username:
        raise AdminConfigurationError("ADMIN_USERNAME не может быть пустым.")
    if len(password) < 8:
        raise AdminConfigurationError(
            "ADMIN_PASSWORD должен содержать минимум 8 символов."
        )
    return create_initial_admin(
        db=db,
        username=normalized_username,
        password_hash=hash_password(password),
    )


def authenticate_admin(
    db: Session,
    username: str,
    password: str,
) -> AdminCredential | None:
    """Проверяет логин и пароль единственного администратора."""
    admin = get_admin(db)
    if admin is None:
        return None
    if not secrets_match(username.strip(), admin.username):
        return None
    if not verify_password(password, admin.password_hash):
        return None
    return admin


def change_admin_credentials(
    db: Session,
    admin: AdminCredential,
    current_password: str,
    new_username: str,
    new_password: str,
    new_password_confirm: str,
) -> tuple[AdminCredential, bool]:
    """Проверяет форму и обновляет логин или пароль администратора."""
    if not verify_password(current_password, admin.password_hash):
        raise ValueError("Текущий пароль указан неверно.")

    normalized_username = new_username.strip() or admin.username
    if len(normalized_username) > 128:
        raise ValueError("Логин не должен превышать 128 символов.")

    password_changed = bool(new_password)
    password_hash = None
    if password_changed:
        if len(new_password) < 8:
            raise ValueError("Новый пароль должен содержать минимум 8 символов.")
        if new_password != new_password_confirm:
            raise ValueError("Новый пароль и повтор пароля не совпадают.")
        password_hash = hash_password(new_password)
    elif new_password_confirm:
        raise ValueError("Введите новый пароль перед его повтором.")

    return (
        update_admin_credentials(
            db=db,
            admin=admin,
            username=normalized_username,
            password_hash=password_hash,
        ),
        password_changed,
    )


def secrets_match(first: str, second: str) -> bool:
    """Сравнивает логины одинаковым способом с паролями."""
    import hmac

    return hmac.compare_digest(first.encode("utf-8"), second.encode("utf-8"))
