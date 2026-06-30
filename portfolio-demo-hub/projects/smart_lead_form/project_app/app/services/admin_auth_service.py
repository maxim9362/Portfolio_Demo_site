# Provides admin login, password hashing, and credential management.

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.admin_user import AdminUser

HASH_ALGORITHM = "pbkdf2_sha256"
HASH_ITERATIONS = 260_000
SESSION_TOKENS: dict[str, int] = {}


@dataclass(frozen=True)
class AuthenticatedAdmin:
    id: int
    client_id: str
    username: str


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        HASH_ITERATIONS,
    ).hex()
    return f"{HASH_ALGORITHM}${HASH_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = stored_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != HASH_ALGORITHM:
        return False

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    ).hex()
    return hmac.compare_digest(digest, expected)


def get_admin_user(db: Session, client_id: str) -> AdminUser | None:
    return db.query(AdminUser).filter(AdminUser.client_id == client_id).first()


def ensure_default_admin_user(db: Session) -> AdminUser:
    admin_user = get_admin_user(db, settings.default_client_id)
    if admin_user:
        return admin_user

    admin_user = AdminUser(
        client_id=settings.default_client_id,
        username=settings.admin_username,
        password_hash=hash_password(settings.admin_password),
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    return admin_user


def authenticate_admin(db: Session, client_id: str, username: str, password: str) -> AdminUser | None:
    admin_user = get_admin_user(db, client_id)
    if not admin_user:
        return None

    if admin_user.username != username:
        return None

    if not verify_password(password, admin_user.password_hash):
        return None

    return admin_user


def create_access_token(admin_user: AdminUser) -> str:
    token = secrets.token_urlsafe(32)
    SESSION_TOKENS[token] = admin_user.id
    return token


def get_admin_by_token(db: Session, token: str) -> AdminUser | None:
    admin_user_id = SESSION_TOKENS.get(token)
    if not admin_user_id:
        return None

    return db.query(AdminUser).filter(AdminUser.id == admin_user_id).first()


def update_admin_credentials(
    db: Session,
    admin_user: AdminUser,
    current_password: str,
    new_username: str,
    new_password: str,
) -> AdminUser:
    if not verify_password(current_password, admin_user.password_hash):
        raise ValueError("Invalid current password")

    admin_user.username = new_username
    admin_user.password_hash = hash_password(new_password)
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    return admin_user
