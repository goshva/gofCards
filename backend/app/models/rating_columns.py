"""Mixin holding the derived rating block shared by players and teams.

Everything here is computed from real GoFuture match results by
services/ratings.py; the public API exposes no per-player statistics.
"""
from __future__ import annotations

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column


class RatingMixin:
    ovr: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False, index=True)
    rank: Mapped[int | None] = mapped_column(Integer, index=True)

    atk: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    deff: Mapped[int] = mapped_column("def", Integer, default=0, server_default="0", nullable=False)
    dig: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    phy: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    clt: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    exp: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    matches_played: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    wins: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    draws: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    losses: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    goals_for: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    goals_against: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    best_round: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    @property
    def attributes(self) -> dict[str, int]:
        return {
            "atk": self.atk,
            "def": self.deff,
            "dig": self.dig,
            "phy": self.phy,
            "clt": self.clt,
            "exp": self.exp,
        }
