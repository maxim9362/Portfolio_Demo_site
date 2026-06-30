# Этот файл хеширует пароли и защищает административные POST-формы.

import base64
import hashlib
import hmac
import secrets

from starlette.requests import Request


SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_LENGTH = 64


def hash_password(password: str) -> str:
    """Создает соленый scrypt-хеш пароля для хранения в PostgreSQL."""
    if len(password) < 8:
        raise ValueError("Пароль должен содержать минимум 8 символов.")

    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_LENGTH,
    )
    return "$".join(
        (
            "scrypt",
            str(SCRYPT_N),
            str(SCRYPT_R),
            str(SCRYPT_P),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        )
    )


def verify_password(password: str, password_hash: str) -> bool:
    """Безопасно сравнивает введенный пароль с сохраненным scrypt-хешем."""
    try:
        algorithm, n, r, p, salt_text, digest_text = password_hash.split("$")
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def get_csrf_token(request: Request) -> str:
    """Возвращает постоянный CSRF-токен текущей cookie-сессии."""
    token = request.session.get("csrf_token")
    if not isinstance(token, str) or not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def validate_csrf_token(request: Request, submitted_token: str) -> bool:
    """Проверяет CSRF-токен формы без утечки времени сравнения."""
    expected = request.session.get("csrf_token")
    return bool(
        isinstance(expected, str)
        and submitted_token
        and hmac.compare_digest(expected, submitted_token)
    )
