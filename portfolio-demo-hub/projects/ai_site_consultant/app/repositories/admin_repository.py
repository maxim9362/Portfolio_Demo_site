# Этот файл управляет единственной учетной записью администратора.

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.admin_credential import AdminCredential


def get_admin(db: Session) -> AdminCredential | None:
    """Возвращает единственную учетную запись администратора."""
    return db.scalar(
        select(AdminCredential).order_by(AdminCredential.id.asc()).limit(1)
    )


def create_initial_admin(
    db: Session,
    username: str,
    password_hash: str,
) -> AdminCredential:
    """Создает первого администратора, только если таблица еще пуста."""
    existing = get_admin(db)
    if existing is not None:
        return existing

    admin = AdminCredential(
        username=username.strip(),
        password_hash=password_hash,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def update_admin_credentials(
    db: Session,
    admin: AdminCredential,
    username: str,
    password_hash: str | None = None,
) -> AdminCredential:
    """Обновляет логин и при необходимости хеш пароля администратора."""
    admin.username = username.strip()
    if password_hash is not None:
        admin.password_hash = password_hash
    db.commit()
    db.refresh(admin)
    return admin
