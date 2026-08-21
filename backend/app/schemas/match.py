from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.base import MatchStatus
from app.schemas.card import PlayerBrief, TeamBrief
from app.schemas.common import ORMModel


class MatchScore(BaseModel):
    total: dict[str, int]
    digital: dict[str, int]
    physical: dict[str, int]
    shootouts: dict[str, int]


class MatchOut(ORMModel):
    id: int
    slug: str
    external_id: str
    tournament_slug: str
    round: int | None = None
    round_label: str | None = None
    venue: str | None = None
    status: MatchStatus
    start_time: datetime | None = None
    home_team: TeamBrief | None = None
    away_team: TeamBrief | None = None
    home_score: int
    away_score: int
    home_digital: int
    away_digital: int
    home_physical: int
    away_physical: int
    home_shootouts: int
    away_shootouts: int
    winner_team_id: int | None = None
    has_lineups: bool = False
    lineups_source: str | None = None
    points_calculated: bool = False


class MatchLineups(BaseModel):
    match_id: int
    source: str | None = None
    home: list[PlayerBrief]
    away: list[PlayerBrief]


class LineupInput(BaseModel):
    home_player_ids: list[int]
    away_player_ids: list[int]


class PlayerStatInput(BaseModel):
    player_id: int
    started: bool = True
    goals: int = 0
    assists: int = 0
    saves: int = 0
    own_goals: int = 0
    yellow_cards: int = 0
    red_cards: int = 0


class MatchStatsInput(BaseModel):
    stats: list[PlayerStatInput]
