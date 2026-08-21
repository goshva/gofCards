from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import NotFound
from app.models import (
    CardType,
    Position,
    Pack,
    Player,
    PlayerCardTemplate,
    Rarity,
    Team,
    TeamCardTemplate,
    UserCard,
)
from app.schemas.card import (
    CardTemplateOut,
    CollectionStats,
    OpenPackRequest,
    OpenPackResult,
    PackOut,
    PlayerBrief,
    RankingRow,
    UserCardOut,
)
from app.schemas.common import Page
from app.services import catalog
from app.services.card_service import CardService
from app.services.ratings import rarities_for_rank

router = APIRouter(prefix="/cards", tags=["cards"])


@router.get("/templates", response_model=Page[CardTemplateOut])
async def list_templates(
    db: DbSession,
    card_type: CardType | None = None,
    rarity: Rarity | None = None,
    team_id: int | None = None,
    search: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[CardTemplateOut]:
    items: list[CardTemplateOut] = []
    total = 0

    if card_type in (None, CardType.PLAYER):
        stmt = select(PlayerCardTemplate).join(Player, Player.id == PlayerCardTemplate.player_id)
        if rarity:
            stmt = stmt.where(PlayerCardTemplate.rarity == rarity)
        if team_id:
            stmt = stmt.where(Player.team_id == team_id)
        if search:
            stmt = stmt.where(Player.nickname.ilike(f"%{search}%"))
        total += await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = await db.scalars(stmt.order_by(PlayerCardTemplate.id).limit(limit).offset(offset))
        items.extend(catalog.player_template_out(t) for t in rows)

    if card_type in (None, CardType.TEAM) and len(items) < limit:
        stmt = select(TeamCardTemplate).join(Team, Team.id == TeamCardTemplate.team_id)
        if rarity:
            stmt = stmt.where(TeamCardTemplate.rarity == rarity)
        if team_id:
            stmt = stmt.where(TeamCardTemplate.team_id == team_id)
        if search:
            stmt = stmt.where(Team.title.ilike(f"%{search}%"))
        total += await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = await db.scalars(stmt.order_by(TeamCardTemplate.id).limit(limit - len(items)))
        items.extend(catalog.team_template_out(t) for t in rows)

    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/my-collection", response_model=Page[UserCardOut])
async def my_collection(
    db: DbSession,
    user: CurrentUser,
    card_type: CardType | None = None,
    rarity: Rarity | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[UserCardOut]:
    stmt = select(UserCard).where(UserCard.user_id == user.id)
    if card_type:
        stmt = stmt.where(UserCard.card_type == card_type)
    cards = list(await db.scalars(stmt.order_by(UserCard.acquired_at.desc())))

    serialized = await CardService(db).serialize(user.id, cards)
    if rarity:
        serialized = [c for c in serialized if c.template.rarity == rarity]
    return Page(
        items=serialized[offset : offset + limit],
        total=len(serialized),
        limit=limit,
        offset=offset,
    )


@router.get("/my-collection/stats", response_model=CollectionStats)
async def collection_stats(db: DbSession, user: CurrentUser) -> CollectionStats:
    return CollectionStats(**await CardService(db).collection_stats(user.id))


@router.get("/packs", response_model=list[PackOut])
async def list_packs(db: DbSession) -> list[PackOut]:
    rows = await db.scalars(select(Pack).where(Pack.is_active.is_(True)).order_by(Pack.price))
    return [PackOut.model_validate(p) for p in rows]


@router.post("/open-pack", response_model=OpenPackResult)
async def open_pack(payload: OpenPackRequest, db: DbSession, user: CurrentUser) -> OpenPackResult:
    pack = await db.get(Pack, payload.pack_id)
    if pack is None:
        raise NotFound("Бустер не найден")
    opening, cards = await CardService(db).open_pack(user, pack)
    return OpenPackResult(
        opening_id=opening.id,
        pack_id=pack.id,
        coins_spent=opening.coins_spent,
        coins_left=user.coins,
        cards=await catalog.serialize_cards(db, cards),
    )


@router.get("/ranking", response_model=list[RankingRow])
async def ranking(
    db: DbSession,
    user: CurrentUser,
    position: Position | None = None,
    team_id: int | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[RankingRow]:
    """Players ordered by the rating derived from real tournament results."""
    stmt = select(Player).where(Player.rank.isnot(None))
    if position:
        stmt = stmt.where(Player.position == position)
    if team_id:
        stmt = stmt.where(Player.team_id == team_id)
    players = list(await db.scalars(stmt.order_by(Player.rank).limit(limit).offset(offset)))

    owned_rows = (
        await db.execute(
            select(PlayerCardTemplate.player_id, func.count())
            .join(UserCard, UserCard.card_template_id == PlayerCardTemplate.id)
            .where(UserCard.user_id == user.id, UserCard.card_type == CardType.PLAYER)
            .group_by(PlayerCardTemplate.player_id)
        )
    ).all()
    owned = dict(owned_rows)

    return [
        RankingRow(
            rank=p.rank or 0,
            ovr=p.ovr,
            player=PlayerBrief.model_validate(p),
            rarities=[Rarity(name) for name in rarities_for_rank(p.rank)],
            owned=owned.get(p.id, 0),
        )
        for p in players
    ]
