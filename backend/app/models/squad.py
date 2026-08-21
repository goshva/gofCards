from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PositionSlot, created_at_col, str_enum, uuid_pk


class SquadEntry(Base):
    """One slot of a user squad.

    match_id NULL means the working draft squad; a non-null match_id is the
    snapshot locked in for that match and used by scoring.
    """

    __tablename__ = "squad_entries"
    __table_args__ = (
        UniqueConstraint("user_id", "match_id", "position_slot", name="uq_squad_slot"),
        UniqueConstraint("user_id", "match_id", "player_id", name="uq_squad_player"),
    )

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    user_card_id: Mapped[str] = mapped_column(ForeignKey("user_cards.id", ondelete="CASCADE"), nullable=False)
    position_slot: Mapped[PositionSlot] = mapped_column(str_enum(PositionSlot, "position_slot"), nullable=False)
    is_captain: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_vice_captain: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = created_at_col()

    player = relationship("Player", lazy="selectin")
    card = relationship("UserCard", lazy="selectin")

    @property
    def is_starter(self) -> bool:
        return self.position_slot not in (PositionSlot.SUB1, PositionSlot.SUB2)
