from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import STARTING_COINS
from app.models.base import Base, UserRole, created_at_col, str_enum, uuid_pk


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = uuid_pk()
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(str_enum(UserRole, "user_role"), default=UserRole.USER, nullable=False)
    coins: Mapped[int] = mapped_column(Integer, default=STARTING_COINS, nullable=False)
    total_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # short shareable code used by the invite-a-friend quest
    referral_code: Mapped[str | None] = mapped_column(String(16), unique=True, index=True)
    created_at: Mapped[datetime] = created_at_col()

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN
