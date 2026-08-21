from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RetiredCard(BaseModel):
    nickname: str | None = None
    ovr: int | None = None
    slot: str | None = None


class SquadSlotOut(BaseModel):
    user_card_id: str | None = None
    is_permanent: bool = False
    runs_left: int | None = None
    slot: str
    player_id: int
    nickname: str
    team: str | None = None
    rarity: str | None = None
    ovr: int
    is_captain: bool


class ReplacedTeamOut(BaseModel):
    id: int
    title: str
    ovr: int
    rank: int | None = None
    record: str


class FirstMatchOut(BaseModel):
    label: str
    opponent: str
    opponent_ovr: int
    win_chance: float | None = None


class TournamentPreview(BaseModel):
    tournament_slug: str
    entry_fee: int
    cooldown_seconds: int = 0
    squad_ovr: int
    squad: list[SquadSlotOut]
    replaced_team: ReplacedTeamOut
    first_match: FirstMatchOut | None = None
    coins_per_stage: int
    points_per_stage: int


class RunSide(BaseModel):
    name: str
    ovr: int
    is_user: bool


class RunMatch(BaseModel):
    match_id: int
    label: str
    stage: str
    source: str
    home: RunSide
    away: RunSide
    home_score: int
    away_score: int
    digital: list[int]
    physical: list[int]
    shootout: list[int] | None = None
    winner: str
    user_involved: bool
    user_won: bool
    user_win_chance: float | None = None


class TournamentEntryOut(BaseModel):
    id: str
    tournament_slug: str
    seed: str
    squad_ovr: int
    squad: list[SquadSlotOut]
    replaced_team: ReplacedTeamOut | None = None
    stage: str
    stage_label: str
    stage_index: int
    played: int
    wins: int
    losses: int
    entry_fee: int
    coins_awarded: int
    points_awarded: int
    coins_net: int
    retired: list[RetiredCard] = []
    my_matches: list[RunMatch]
    full_run: list[RunMatch] = []
    created_at: datetime


class EnterRequest(BaseModel):
    tournament_slug: str | None = None
