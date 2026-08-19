from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator, model_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(value: str) -> str:
    email = value.strip().lower()
    if not EMAIL_RE.match(email):
        raise ValueError("Invalid email address")
    return email


class RegisterRequest(BaseModel):
    roll_number: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    email: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _validate_email(value)


class LoginRequest(BaseModel):
    """Authenticate with either roll_number or email."""

    roll_number: str | None = None
    email: str | None = None
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_email(value)

    @model_validator(mode="after")
    def require_identifier(self) -> "LoginRequest":
        if not self.roll_number and not self.email:
            raise ValueError("Provide roll_number or email")
        return self


class UserResponse(BaseModel):
    roll_number: str
    name: str
    email: str
    is_admin: bool = False

    model_config = {"from_attributes": True}



class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
