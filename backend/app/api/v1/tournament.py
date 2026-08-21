from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.constants import TOURNAMENT
from app.core.exceptions import NotFound
from app.models import TournamentEntry
from app.schemas.tournament import EnterRequest, TournamentEntryOut, TournamentPreview
from app.services.tournament_service import TournamentService

router = APIRouter(prefix="/tournament", tags=["tournament"])

STAGE_LABELS: dict[str, str] = TOURNAMENT["stageLabels"]


def _serialize(entry: TournamentEntry, *, full: bool = False) -> TournamentEntryOut:
    team = entry.replaced_team
    return TournamentEntryOut(
        id=entry.id,
        tournament_slug=entry.tournament_slug,
        seed=entry.seed,
        squad_ovr=entry.squad_ovr,
        squad=entry.squad_json,
        replaced_team=(
            {
                "id": team.id,
                "title": team.title,
                "ovr": team.ovr,
                "rank": team.rank,
                "record": f"{team.wins}-{team.draws}-{team.losses}",
            }
            if team
            else None
        ),
        stage=entry.stage,
        stage_label=STAGE_LABELS.get(entry.stage, entry.stage),
        stage_index=entry.stage_index,
        played=entry.played,
        wins=entry.wins,
        losses=entry.losses,
        entry_fee=entry.entry_fee,
        coins_awarded=entry.coins_awarded,
        points_awarded=entry.points_awarded,
        coins_net=entry.coins_awarded - entry.entry_fee,
        retired=entry.retired_json or [],
        my_matches=[m for m in entry.run_json if m.get("user_involved")],
        full_run=entry.run_json if full else [],
        created_at=entry.created_at,
    )


@router.get("/preview", response_model=TournamentPreview)
async def preview(
    db: DbSession, user: CurrentUser, tournament_slug: str | None = None
) -> TournamentPreview:
    """Who you replace, who you meet first and what the odds are."""
    slug = tournament_slug or settings.gofuture_tournament_slug
    return TournamentPreview(**await TournamentService(db).preview(user, slug))


@router.post("/enter", response_model=TournamentEntryOut)
async def enter(payload: EnterRequest, db: DbSession, user: CurrentUser) -> TournamentEntryOut:
    slug = payload.tournament_slug or settings.gofuture_tournament_slug
    entry = await TournamentService(db).enter(user, slug)
    return _serialize(entry, full=True)


@router.get("/entries", response_model=list[TournamentEntryOut])
async def entries(
    db: DbSession, user: CurrentUser, limit: Annotated[int, Query(ge=1, le=50)] = 20
) -> list[TournamentEntryOut]:
    rows = await db.scalars(
        select(TournamentEntry)
        .where(TournamentEntry.user_id == user.id)
        .order_by(TournamentEntry.created_at.desc())
        .limit(limit)
    )
    return [_serialize(e) for e in rows]


@router.get("/entries/{entry_id}", response_model=TournamentEntryOut)
async def entry_detail(entry_id: str, db: DbSession, user: CurrentUser) -> TournamentEntryOut:
    """The full bracket of a run, including the fixtures you were not part of."""
    entry = await db.get(TournamentEntry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise NotFound("Заявка не найдена")
    return _serialize(entry, full=True)
