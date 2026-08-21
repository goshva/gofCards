from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, created_at_col, uuid_pk


class TournamentEntry(Base):
    """One run of a user squad through the real tournament bracket.

    The squad takes the slot of the weakest team, so every other pairing keeps
    its historical result and only the matches the user is involved in are
    played out. The draw seed is stored, which makes a run reproducible and
    therefore auditable.
    """

    __tablename__ = "tournament_entries"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    tournament_slug: Mapped[str] = mapped_column(String(128), index=True, nullable=False)

    seed: Mapped[str] = mapped_column(String(32), nullable=False)
    replaced_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"))
    squad_ovr: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    squad_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)

    stage: Mapped[str] = mapped_column(String(16), default="NONE", nullable=False)
    stage_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    draws: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    entry_fee: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coins_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    points_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    run_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    # cards that used up their last run in this tournament
    retired_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, server_default="[]", nullable=False
    )
    created_at: Mapped[datetime] = created_at_col()
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    replaced_team = relationship("Team", lazy="selectin")
