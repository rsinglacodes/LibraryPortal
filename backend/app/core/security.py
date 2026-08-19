from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings

BCRYPT_PREFIXES = ("$2a$", "$2b$", "$2y$")


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt for new/real users."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def _is_bcrypt_hash(password_hash: str) -> bool:
    return password_hash.startswith(BCRYPT_PREFIXES)


def _is_sha256_hex(password_hash: str) -> bool:
    if len(password_hash) != 64:
        return False
    try:
        int(password_hash, 16)
        return True
    except ValueError:
        return False


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against a stored hash.

    Supports:
    - bcrypt (new registrations / upgraded seed users)
    - SHA-256 hex (legacy seed users from Stage 2A)
    """
    if _is_bcrypt_hash(password_hash):
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                password_hash.encode("utf-8"),
            )
        except ValueError:
            return False

    if _is_sha256_hex(password_hash):
        digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return digest == password_hash.lower()

    return False


def needs_rehash(password_hash: str) -> bool:
    """True when the stored hash should be upgraded to bcrypt."""
    return not _is_bcrypt_hash(password_hash)


def create_access_token(*, subject: str) -> str:
    settings = get_settings()
    if not settings.JWT_SECRET:
        raise RuntimeError("JWT_SECRET is not configured")

    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> str:
    """Return the roll_number (sub) from a valid JWT."""
    settings = get_settings()
    if not settings.JWT_SECRET:
        raise RuntimeError("JWT_SECRET is not configured")

    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )
    subject = payload.get("sub")
    if not subject or not isinstance(subject, str):
        raise jwt.InvalidTokenError("Token missing subject")
    return subject
