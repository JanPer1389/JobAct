"""HTTP-layer Pydantic response DTOs for the `/api/v1/auth/*` routes.

Deliberately separate from `contexts.identity.domain.session.Session`
(a domain aggregate) and `contexts.identity.application
.sign_in_with_google.SignInResult` (an application-layer dataclass) --
this module is the ONLY place the actual JSON shape returned to HTTP
clients is defined. Pydantic-only (plus stdlib): no FastAPI, no
SQLAlchemy.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    repeat_password: str = Field(max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.repeat_password:
            raise ValueError("Passwords do not match.")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class PasswordUpdateRequest(BaseModel):
    current_password: str | None = Field(default=None, max_length=128)
    new_password: str = Field(
        min_length=12, max_length=128
    )
    repeat_password: str = Field(max_length=128)

    @model_validator(mode="after")
    def passwords_match(self) -> "PasswordUpdateRequest":
        if self.new_password != self.repeat_password:
            raise ValueError("Passwords do not match.")
        return self


class AuthMethodsResponse(BaseModel):
    password: bool
    google: bool


class LocaleUpdateRequest(BaseModel):
    locale: Literal["en-US", "ru-RU"]


class CurrencyUpdateRequest(BaseModel):
    currency: Literal["USD", "RUB"]


class SessionResponse(BaseModel):
    """Body of a successful `GET /api/v1/auth/session` response.

    Mirrors `apps.api.deps.CurrentPrincipal` exactly -- the fields
    available on every authenticated request without an extra Postgres
    lookup for the `User` aggregate (e.g. email). Extending this to
    include profile fields is a later task's job if/when a route
    actually needs them.
    """

    user_id: UUID
    organization_id: UUID
    role: str
    locale: Literal["en-US", "ru-RU"]
    currency: Literal["USD", "RUB"]
