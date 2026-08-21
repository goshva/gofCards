from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.base import TradeStatus
from app.schemas.card import UserCardOut
from app.schemas.user import UserPublic


class TradeCreate(BaseModel):
    receiver_id: str
    sender_cards: list[str] = Field(default_factory=list)
    receiver_cards: list[str] = Field(default_factory=list)
    sender_coins: int = Field(default=0, ge=0)
    message: str | None = Field(default=None, max_length=512)

    @model_validator(mode="after")
    def not_empty(self) -> "TradeCreate":
        if not self.sender_cards and not self.receiver_cards and not self.sender_coins:
            raise ValueError("Предложение обмена не может быть пустым")
        if len(set(self.sender_cards)) != len(self.sender_cards):
            raise ValueError("Дубликаты в списке своих карточек")
        if len(set(self.receiver_cards)) != len(self.receiver_cards):
            raise ValueError("Дубликаты в списке запрашиваемых карточек")
        return self


class TradeCounter(BaseModel):
    sender_cards: list[str] = Field(default_factory=list)
    receiver_cards: list[str] = Field(default_factory=list)
    sender_coins: int = Field(default=0, ge=0)
    message: str | None = Field(default=None, max_length=512)


class TradeOfferOut(BaseModel):
    id: str
    status: TradeStatus
    sender: UserPublic
    receiver: UserPublic
    sender_cards: list[UserCardOut]
    receiver_cards: list[UserCardOut]
    sender_coins: int
    message: str | None = None
    counter_of_id: str | None = None
    created_at: datetime
    updated_at: datetime
