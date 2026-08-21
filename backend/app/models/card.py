from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CardType, Rarity, created_at_col, str_enum, uuid_pk


class PlayerCardTemplate(Base):
    __tablename__ = "player_card_templates"
    __table_args__ = (UniqueConstraint("player_id", "rarity", name="uq_player_rarity"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"), index=True, nullable=False)
    rarity: Mapped[Rarity] = mapped_column(str_enum(Rarity, "rarity"), nullable=False, index=True)
    base_price: Mapped[int] = mapped_column(Integer, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(2048))

    player = relationship("Player", lazy="selectin")

    card_type = CardType.PLAYER


class TeamCardTemplate(Base):
    __tablename__ = "team_card_templates"
    __table_args__ = (UniqueConstraint("team_id", "rarity", name="uq_team_rarity"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False)
    rarity: Mapped[Rarity] = mapped_column(str_enum(Rarity, "rarity"), nullable=False, index=True)
    base_price: Mapped[int] = mapped_column(Integer, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(2048))

    team = relationship("Team", lazy="selectin")

    card_type = CardType.TEAM


class UserCard(Base):
    """One owned copy of a card.

    Duplicates are separate rows so every copy can be traded independently.
    An ordinary card wears out: fielding it in a tournament spends one of its
    six runs and it is discarded when the last one is used. A permanent card,
    pulled from the collector booster, never wears out.
    """

    __tablename__ = "user_cards"
    __table_args__ = (Index("ix_user_cards_owner_template", "user_id", "card_type", "card_template_id"),)

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    card_template_id: Mapped[int] = mapped_column(Integer, nullable=False)
    card_type: Mapped[CardType] = mapped_column(str_enum(CardType, "card_type"), nullable=False)
    acquired_at: Mapped[datetime] = created_at_col()
    source: Mapped[str] = mapped_column(String(32), default="pack", nullable=False)
    is_permanent: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )
    tournaments_used: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )

    @property
    def runs_left(self) -> int | None:
        """None means the card never expires."""
        from app.core.constants import TOURNAMENT_LIFESPAN

        if self.is_permanent:
            return None
        return max(0, TOURNAMENT_LIFESPAN - self.tournaments_used)
