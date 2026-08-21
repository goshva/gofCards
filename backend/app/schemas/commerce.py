from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.commerce import PaymentStatus


class ProductOut(BaseModel):
    sku: str
    title: str
    subtitle: str | None = None
    price: int
    currency: str
    provider: str
    packId: int | None = None
    quantity: int | None = None
    coins: int | None = None


class CheckoutRequest(BaseModel):
    sku: str


class ConfirmRequest(BaseModel):
    # the sandbox lets the caller choose how the "provider" answers
    outcome: str = Field(default="success", pattern="^(success|failure)$")


class PaymentOut(BaseModel):
    id: str
    sku: str
    title: str
    amount: int
    currency: str
    provider: str
    status: PaymentStatus
    reference: str
    failure_reason: str | None = None
    delivered: dict[str, Any] | None = None
    created_at: datetime
    completed_at: datetime | None = None


class TestCard(BaseModel):
    number: str
    expiry: str
    cvc: str


class CheckoutOut(BaseModel):
    payment: PaymentOut
    test_card: TestCard
    sandbox: bool = True
    notice: str


class QuestOut(BaseModel):
    key: str
    title: str
    description: str
    reward: int
    icon: str | None = None
    url: str | None = None
    repeatable: bool = False
    referral: bool = False
    status: str
    times_claimed: int = 0
    coins_earned: int = 0
    cooldown_seconds: int = 0
    started: bool = False


class QuestBoard(BaseModel):
    quests: list[QuestOut]
    referral_code: str
    referral_reward: int
    referral_friend_bonus: int
    friends_invited: int
    total_earned: int


class ClaimResult(BaseModel):
    quest: QuestOut
    reward: int
    coins: int
