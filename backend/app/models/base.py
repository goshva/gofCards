from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def uuid_pk() -> Mapped[str]:
    return mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def created_at_col() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


def str_enum(enum_cls: type[enum.Enum], name: str) -> SAEnum:
    """String-backed enum: portable between sqlite and postgres, readable in dumps."""
    return SAEnum(enum_cls, name=name, native_enum=False, length=32, values_callable=lambda e: [m.value for m in e])


class Rarity(str, enum.Enum):
    COMMON = "COMMON"
    RARE = "RARE"
    EPIC = "EPIC"
    LEGENDARY = "LEGENDARY"


class CardType(str, enum.Enum):
    PLAYER = "PLAYER"
    TEAM = "TEAM"


class Position(str, enum.Enum):
    GOALKEEPER = "GOALKEEPER"
    FIELD = "FIELD"


class PositionSlot(str, enum.Enum):
    GK = "GK"
    F1 = "F1"
    F2 = "F2"
    F3 = "F3"
    F4 = "F4"
    SUB1 = "SUB1"
    SUB2 = "SUB2"


class MatchStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TradeStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    CANCELLED = "CANCELLED"
    COUNTERED = "COUNTERED"


class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"
