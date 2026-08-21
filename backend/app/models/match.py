from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, MatchStatus, str_enum, uuid_pk


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    tournament_slug: Mapped[str] = mapped_column(String(128), index=True, nullable=False)

    home_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    away_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), index=True)

    round: Mapped[int | None] = mapped_column(Integer)
    round_label: Mapped[str | None] = mapped_column(String(128))
    venue: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[MatchStatus] = mapped_column(
        str_enum(MatchStatus, "match_status"), default=MatchStatus.SCHEDULED, nullable=False, index=True
    )

    home_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    away_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    home_digital: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    away_digital: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    home_physical: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    away_physical: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    home_shootouts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    away_shootouts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    winner_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"))
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    stats_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    home_lineup_json: Mapped[list[str] | None] = mapped_column(JSON)
    away_lineup_json: Mapped[list[str] | None] = mapped_column(JSON)
    lineups_source: Mapped[str | None] = mapped_column(String(16))

    points_calculated: Mapped[bool] = mapped_column(default=False, nullable=False)

    home_team = relationship("Team", foreign_keys=[home_team_id], lazy="selectin")
    away_team = relationship("Team", foreign_keys=[away_team_id], lazy="selectin")


class PlayerMatchStat(Base):
    __tablename__ = "player_match_stats"
    __table_args__ = (UniqueConstraint("match_id", "player_id", name="uq_stat_match_player"),)

    id: Mapped[str] = uuid_pk()
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True, nullable=False)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"), index=True, nullable=False)

    started: Mapped[bool] = mapped_column(default=True, nullable=False)
    goals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    assists: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    saves: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    own_goals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    yellow_cards: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    red_cards: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    player = relationship("Player", lazy="selectin")
