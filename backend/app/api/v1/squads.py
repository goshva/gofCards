from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import NotFound
from app.models import Match, Player, PositionSlot
from app.schemas.card import PlayerBrief
from app.schemas.match import MatchLineups
from app.schemas.squad import (
    CaptainRequest,
    PerfectFiveComparison,
    SelectPlayerRequest,
    SquadOut,
    ValidationResult,
)
from app.services.squad_service import SquadService

router = APIRouter(prefix="/squad", tags=["squad"])


@router.get("/current", response_model=SquadOut)
async def current(db: DbSession, user: CurrentUser, match_id: int | None = None) -> SquadOut:
    return await SquadService(db).serialize(user, match_id)


@router.post("/select", response_model=SquadOut)
async def select_player(
    payload: SelectPlayerRequest, db: DbSession, user: CurrentUser
) -> SquadOut:
    service = SquadService(db)
    await service.select_player(user, payload.user_card_id, payload.position_slot, payload.match_id)
    return await service.serialize(user, payload.match_id)


@router.delete("/remove/{slot}", response_model=SquadOut)
async def remove_slot(
    slot: PositionSlot, db: DbSession, user: CurrentUser, match_id: int | None = None
) -> SquadOut:
    service = SquadService(db)
    await service.remove_slot(user, slot, match_id)
    return await service.serialize(user, match_id)


@router.post("/captain", response_model=SquadOut)
async def set_captain(payload: CaptainRequest, db: DbSession, user: CurrentUser) -> SquadOut:
    service = SquadService(db)
    await service.set_captain(user, payload.entry_id, payload.vice, payload.match_id)
    return await service.serialize(user, payload.match_id)


@router.post("/validate", response_model=ValidationResult)
async def validate(
    db: DbSession, user: CurrentUser, match_id: int | None = None
) -> ValidationResult:
    return await SquadService(db).validate(user, match_id)


@router.post("/lock/{match_id}", response_model=SquadOut)
async def lock_for_match(match_id: int, db: DbSession, user: CurrentUser) -> SquadOut:
    """Freeze the current draft as the squad fielded for this match."""
    service = SquadService(db)
    await service.lock_for_match(user, match_id)
    return await service.serialize(user, match_id)


@router.get("/perfect-xi/{match_id}", response_model=PerfectFiveComparison)
async def perfect_five(match_id: int, db: DbSession, user: CurrentUser) -> PerfectFiveComparison:
    return await SquadService(db).compare_perfect_five(user, match_id)


@router.get("/lineups/{match_id}", response_model=MatchLineups)
async def match_lineups(match_id: int, db: DbSession, user: CurrentUser) -> MatchLineups:
    match = await db.get(Match, match_id)
    if match is None:
        raise NotFound("Матч не найден")
    service = SquadService(db)
    home_ids = await service._lineup_to_player_ids(match.home_lineup_json or [])
    away_ids = await service._lineup_to_player_ids(match.away_lineup_json or [])
    players = {
        p.id: p
        for p in await db.scalars(select(Player).where(Player.id.in_(home_ids + away_ids)))
    }
    return MatchLineups(
        match_id=match_id,
        source=match.lineups_source,
        home=[PlayerBrief.model_validate(players[i]) for i in home_ids if i in players],
        away=[PlayerBrief.model_validate(players[i]) for i in away_ids if i in players],
    )
