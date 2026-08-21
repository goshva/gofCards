from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TradeStatus, created_at_col, str_enum, utcnow, uuid_pk


class TradeOffer(Base):
    __tablename__ = "trade_offers"

    id: Mapped[str] = uuid_pk()
    sender_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    receiver_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[TradeStatus] = mapped_column(
        str_enum(TradeStatus, "trade_status"), default=TradeStatus.PENDING, nullable=False, index=True
    )
    sender_cards: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    receiver_cards: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    sender_coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str | None] = mapped_column(String(512))
    # set when this offer was created as a counter to another one
    counter_of_id: Mapped[str | None] = mapped_column(ForeignKey("trade_offers.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    sender = relationship("User", foreign_keys=[sender_id], lazy="selectin")
    receiver = relationship("User", foreign_keys=[receiver_id], lazy="selectin")

    @property
    def is_open(self) -> bool:
        return self.status == TradeStatus.PENDING
