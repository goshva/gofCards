from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks
from sqlalchemy import select

from app.api.deps import CurrentAdmin, DbSession
from app.core.exceptions import NotFound
from app.models import Match, Player, PlayerMatchStat, SyncState
from app.schemas.common import Message
from app.schemas.leaderboard import SyncStatusOut
from app.schemas.match import LineupInput, MatchStatsInput
from app.services.card_service import CardService
from app.services.scoring import ScoringService
from app.services.sync_service import run_sync_once

router = APIRouter(tags=["admin"])


@router.post("/sync/trigger")
async def trigger_sync(admin: CurrentAdmin, background: BackgroundTasks) -> Message:
    background.add_task(run_sync_once)
    return Message(detail="Синхронизация запущена в фоне")


@router.post("/sync/run-now")
async def run_sync_now(admin: CurrentAdmin) -> dict:
    """Blocking variant, handy for seeding a fresh database."""
    return await run_sync_once()


@router.get("/sync/status", response_model=SyncStatusOut)
async def sync_status(db: DbSession) -> SyncStatusOut:
    state = await db.scalar(select(SyncState).limit(1))
    if state is None:
        return SyncStatusOut(
            last_status="never", teams_synced=0, players_synced=0, matches_synced=0, templates_created=0
        )
    return SyncStatusOut.model_validate(state, from_attributes=True)


@router.post("/admin/matches/{match_id}/lineups")
async def set_lineups(
    match_id: int, payload: LineupInput, db: DbSession, admin: CurrentAdmin
) -> Message:
    """GoFuture leaves lineups empty for this tournament, so Perfect Five only
    becomes checkable once they are entered here."""
    match = await db.get(Match, match_id)
    if match is None:
        raise NotFound("Матч не найден")

    async def to_externals(ids: list[int]) -> list[str]:
        rows = await db.scalars(select(Player).where(Player.id.in_(ids)))
        found = {p.id: p.external_id for p in rows}
        missing = [i for i in ids if i not in found]
        if missing:
            raise NotFound(f"Игроки не найдены: {missing}")
        return [found[i] for i in ids]

    match.home_lineup_json = await to_externals(payload.home_player_ids)
    match.away_lineup_json = await to_externals(payload.away_player_ids)
    match.lineups_source = "admin"
    await db.commit()
    return Message(detail="Составы сохранены")


@router.post("/admin/matches/{match_id}/stats")
async def set_stats(
    match_id: int, payload: MatchStatsInput, db: DbSession, admin: CurrentAdmin
) -> Message:
    match = await db.get(Match, match_id)
    if match is None:
        raise NotFound("Матч не найден")

    for item in payload.stats:
        stat = await db.scalar(
            select(PlayerMatchStat).where(
                PlayerMatchStat.match_id == match_id, PlayerMatchStat.player_id == item.player_id
            )
        )
        if stat is None:
            stat = PlayerMatchStat(match_id=match_id, player_id=item.player_id)
            db.add(stat)
        stat.started = item.started
        stat.goals = item.goals
        stat.assists = item.assists
        stat.saves = item.saves
        stat.own_goals = item.own_goals
        stat.yellow_cards = item.yellow_cards
        stat.red_cards = item.red_cards
    await db.commit()
    return Message(detail=f"Сохранено записей: {len(payload.stats)}")


@router.post("/admin/matches/{match_id}/settle")
async def settle_match(match_id: int, db: DbSession, admin: CurrentAdmin, force: bool = True) -> dict:
    return await ScoringService(db).settle_match(match_id, force=force)


@router.post("/admin/cards/rebuild-templates")
async def rebuild_templates(db: DbSession, admin: CurrentAdmin) -> dict:
    service = CardService(db)
    created = await service.ensure_templates()
    refreshed = await service.refresh_template_images()
    return {"created": created, "images_refreshed": refreshed}
