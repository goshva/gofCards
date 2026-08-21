from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_col, uuid_pk


class Pack(Base):
    __tablename__ = "packs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512))
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    contents_json: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    odds_json: Mapped[dict[str, int] | None] = mapped_column(JSON)
    team_card_chance: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    # the collector booster mints cards that never wear out
    grants_permanent: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )
    # the starter booster always contains a keeper, otherwise a legal squad
    # could be unreachable for a new account
    guarantees_goalkeeper: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )


class PackOpening(Base):
    __tablename__ = "pack_openings"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    pack_id: Mapped[int | None] = mapped_column(ForeignKey("packs.id", ondelete="SET NULL"))
    cards_received: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    coins_spent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    opened_at: Mapped[datetime] = created_at_col()
