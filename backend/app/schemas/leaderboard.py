from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LeaderboardRow(BaseModel):
    rank: int
    user_id: str
    username: str
    total_points: int
    cards_owned: int
    perfect_fives: int


class LeaderboardMe(BaseModel):
    rank: int | None = None
    total_users: int
    row: LeaderboardRow | None = None


class PointsHistoryOut(BaseModel):
    match_id: int
    match_slug: str
    points: int
    is_perfect_xi: bool
    breakdown: dict
    created_at: datetime


class SyncStatusOut(BaseModel):
    last_run_at: datetime | None = None
    last_status: str
    last_error: str | None = None
    teams_synced: int
    players_synced: int
    matches_synced: int
    templates_created: int
