from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.base import PositionSlot
from app.schemas.card import PlayerBrief, UserCardOut


class SquadEntryOut(BaseModel):
    id: str
    position_slot: PositionSlot
    is_captain: bool
    is_vice_captain: bool
    player: PlayerBrief
    card: UserCardOut


class SquadOut(BaseModel):
    match_id: int | None = None
    locked: bool = False
    entries: list[SquadEntryOut]
    filled_slots: int
    required_slots: int


class SelectPlayerRequest(BaseModel):
    user_card_id: str
    position_slot: PositionSlot
    match_id: int | None = None


class CaptainRequest(BaseModel):
    entry_id: str
    vice: bool = False
    match_id: int | None = None


class ValidationIssue(BaseModel):
    code: str
    message: str


class ValidationResult(BaseModel):
    valid: bool
    message: str
    issues: list[ValidationIssue] = Field(default_factory=list)
    is_perfect_five: bool = False
    perfect_five_team: str | None = None


class PerfectFiveComparison(BaseModel):
    match_id: int
    available: bool
    message: str
    is_perfect: bool = False
    matched_team: str | None = None
    home_matches: list[int] = Field(default_factory=list)
    away_matches: list[int] = Field(default_factory=list)
    user_player_ids: list[int] = Field(default_factory=list)
