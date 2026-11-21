"""Request and response shapes for sign up, sign in and the user profile."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.security import is_valid_email, normalize_email, password_problem


class SignupRequest(BaseModel):
    email: str
    password: str
    display_name: str = Field(min_length=1, max_length=100)
    business_name: str | None = Field(default=None, max_length=200)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = normalize_email(v)
        if not is_valid_email(v):
            raise ValueError("Enter a valid email address.")
        return v

    @field_validator("display_name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name is required.")
        return v

    @field_validator("password")
    @classmethod
    def _password(cls, v: str, info) -> str:
        problem = password_problem(v, info.data.get("email", ""))
        if problem:
            raise ValueError(problem)
        return v


class LoginRequest(BaseModel):
    email: str
    password: str = Field(max_length=128)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return normalize_email(v)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str
    business_name: str | None
    phone: str | None
    language: str
    created_at: datetime


class UserUpdate(BaseModel):
    """Only the fields that are sent are changed. Send null to clear business name or phone."""

    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    business_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    language: Literal["en", "bn"] | None = None

    @field_validator("display_name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty.")
        return v


class PasswordChange(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _password(cls, v: str) -> str:
        problem = password_problem(v)
        if problem:
            raise ValueError(problem)
        return v
