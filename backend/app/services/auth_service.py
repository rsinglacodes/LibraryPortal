from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse


def _user_response(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


def register_user(db: Session, payload: RegisterRequest) -> TokenResponse:
    roll_number = payload.roll_number.strip()
    name = payload.name.strip()
    email = payload.email

    if db.get(User, roll_number) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Roll number already registered",
        )

    existing_email = db.scalar(select(User).where(User.email == email))
    if existing_email is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        roll_number=roll_number,
        name=name,
        email=email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(subject=user.roll_number),
        user=_user_response(user),
    )


def login_user(db: Session, payload: LoginRequest) -> TokenResponse:
    user: User | None = None

    if payload.roll_number:
        user = db.get(User, payload.roll_number.strip())
    elif payload.email:
        email = payload.email
        user = db.scalar(select(User).where(User.email == email))

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        db.add(user)
        db.commit()
        db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(subject=user.roll_number),
        user=_user_response(user),
    )
