from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.base import UserRole
from app.schemas.common import ORMModel


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    referral_code: str | None = Field(default=None, max_length=16)


class UserLogin(BaseModel):
    username: str
    password: str


class UserPublic(ORMModel):
    id: str
    username: str
    total_points: int


class UserOut(ORMModel):
    id: str
    username: str
    referral_code: str | None = None
    email: EmailStr
    role: UserRole
    coins: int
    total_points: int
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class RegisterResult(BaseModel):
    token: Token
    # kept at zero: a new account gets coins, and buys its own players
    welcome_cards: int = 0
    referral_bonus: int = 0
