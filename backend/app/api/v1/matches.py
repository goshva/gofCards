from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import DbSession
from app.core.exceptions import NotFound
from app.models import Match, MatchStatus, Player, Team
from app.schemas.card import PlayerBrief, TeamBrief
from app.schemas.common import Page
from app.schemas.match import MatchOut

router = APIRouter(tags=["matches"])


def _to_out(match: Match) -> MatchOut:
    out = MatchOut.model_validate(match)
    out.has_lineups = bool(match.home_lineup_json or match.away_lineup_json)
    return out


@router.get("/matches", response_model=Page[MatchOut])
async def list_matches(
    db: DbSession,
    tournament_slug: str | None = None,
    round: int | None = None,
    status: MatchStatus | None = None,
    team_id: int | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[MatchOut]:
    stmt = select(Match)
    if tournament_slug:
        stmt = stmt.where(Match.tournament_slug == tournament_slug)
    if round is not None:
        stmt = stmt.where(Match.round == round)
    if status:
        stmt = stmt.where(Match.status == status)
    if team_id:
        stmt = stmt.where((Match.home_team_id == team_id) | (Match.away_team_id == team_id))

    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = await db.scalars(
        stmt.order_by(Match.start_time.asc().nulls_last(), Match.id).limit(limit).offset(offset)
    )
    return Page(items=[_to_out(m) for m in rows], total=total, limit=limit, offset=offset)


@router.get("/matches/live", response_model=list[MatchOut])
async def live_matches(db: DbSession) -> list[MatchOut]:
    rows = await db.scalars(
        select(Match).where(Match.status == MatchStatus.LIVE).order_by(Match.start_time)
    )
    return [_to_out(m) for m in rows]


@router.get("/matches/upcoming", response_model=list[MatchOut])
async def upcoming_matches(
    db: DbSession, limit: Annotated[int, Query(ge=1, le=50)] = 10
) -> list[MatchOut]:
    rows = await db.scalars(
        select(Match)
        .where(Match.status == MatchStatus.SCHEDULED)
        .order_by(Match.start_time.asc().nulls_last())
        .limit(limit)
    )
    return [_to_out(m) for m in rows]


@router.get("/matches/{match_id}", response_model=MatchOut)
async def get_match(match_id: int, db: DbSession) -> MatchOut:
    match = await db.get(Match, match_id)
    if match is None:
        raise NotFound("Матч не найден")
    return _to_out(match)


@router.get("/teams", response_model=list[TeamBrief])
async def list_teams(db: DbSession) -> list[TeamBrief]:
    rows = await db.scalars(select(Team).order_by(Team.title))
    return [TeamBrief.model_validate(t) for t in rows]


@router.get("/teams/{team_id}/players", response_model=list[PlayerBrief])
async def team_players(team_id: int, db: DbSession) -> list[PlayerBrief]:
    rows = await db.scalars(
        select(Player).where(Player.team_id == team_id).order_by(Player.position, Player.nickname)
    )
    return [PlayerBrief.model_validate(p) for p in rows]
