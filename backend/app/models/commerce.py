from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, created_at_col, str_enum, uuid_pk


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Payment(Base):
    """A simulated purchase.

    No real provider is involved and no card data is ever accepted or stored:
    the checkout is a sandbox that mimics the states a real integration would
    go through, so swapping in a provider later touches only the confirm step.
    """

    __tablename__ = "payments"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="KZT", nullable=False)
    provider: Mapped[str] = mapped_column(String(32), default="sandbox", nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        str_enum(PaymentStatus, "payment_status"), default=PaymentStatus.PENDING, nullable=False, index=True
    )
    reference: Mapped[str] = mapped_column(String(32), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(255))
    delivered_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = created_at_col()
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class QuestProgress(Base):
    """One quest per user: when it was last claimed and how many times."""

    __tablename__ = "quest_progress"
    __table_args__ = (UniqueConstraint("user_id", "quest_key", name="uq_quest_user_key"),)

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    quest_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    times_claimed: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    coins_earned: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    last_claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # set when a quest needs an action before the reward can be taken
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_col()


class Referral(Base):
    """Who invited whom. One row per invited account, so a friend counts once."""

    __tablename__ = "referrals"
    __table_args__ = (UniqueConstraint("invitee_id", name="uq_referral_invitee"),)

    id: Mapped[str] = uuid_pk()
    inviter_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    invitee_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    inviter_reward: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invitee_reward: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = created_at_col()

    invitee = relationship("User", foreign_keys=[invitee_id], lazy="selectin")
