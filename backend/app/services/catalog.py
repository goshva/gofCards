from __future__ import annotations

from collections.abc import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CardType,
    PlayerCardTemplate,
    SquadEntry,
    TeamCardTemplate,
    TradeOffer,
    TradeStatus,
    UserCard,
)
from app.schemas.card import CardTemplateOut, PlayerBrief, TeamBrief, UserCardOut

# a legendary print of a player is worth a little more than a common one
RARITY_OVR_BOOST = {"COMMON": 0, "RARE": 1, "EPIC": 2, "LEGENDARY": 3}


def player_template_out(tpl: PlayerCardTemplate) -> CardTemplateOut:
    player = tpl.player
    brief = PlayerBrief.model_validate(player)
    # a rarer print of the same athlete reads a couple of points better
    boost = RARITY_OVR_BOOST.get(tpl.rarity.value, 0)
    return CardTemplateOut(
        id=tpl.id,
        card_type=CardType.PLAYER,
        rarity=tpl.rarity,
        base_price=tpl.base_price,
        image_url=brief.photo_url,
        name=player.nickname,
        subtitle=player.team.title if player.team else None,
        position=player.position,
        ovr=min(99, player.ovr + boost) if player.ovr else 0,
        rank=player.rank,
        attributes=player.attributes,
        player=brief,
    )


def team_template_out(tpl: TeamCardTemplate) -> CardTemplateOut:
    team = tpl.team
    brief = TeamBrief.model_validate(team)
    return CardTemplateOut(
        id=tpl.id,
        card_type=CardType.TEAM,
        rarity=tpl.rarity,
        base_price=tpl.base_price,
        image_url=brief.logo_url,
        name=team.title,
        subtitle=team.country,
        ovr=min(99, team.ovr + RARITY_OVR_BOOST.get(tpl.rarity.value, 0)) if team.ovr else 0,
        rank=team.rank,
        attributes=team.attributes,
        team=brief,
    )


async def load_templates(
    db: AsyncSession, refs: Iterable[tuple[CardType, int]]
) -> dict[tuple[CardType, int], CardTemplateOut]:
    """Batch-resolve (card_type, template_id) pairs into presentable templates."""
    player_ids = {tid for ctype, tid in refs if ctype == CardType.PLAYER}
    team_ids = {tid for ctype, tid in refs if ctype == CardType.TEAM}
    out: dict[tuple[CardType, int], CardTemplateOut] = {}

    if player_ids:
        rows = await db.scalars(
            select(PlayerCardTemplate).where(PlayerCardTemplate.id.in_(player_ids))
        )
        for tpl in rows:
            out[(CardType.PLAYER, tpl.id)] = player_template_out(tpl)

    if team_ids:
        rows = await db.scalars(select(TeamCardTemplate).where(TeamCardTemplate.id.in_(team_ids)))
        for tpl in rows:
            out[(CardType.TEAM, tpl.id)] = team_template_out(tpl)

    return out


async def locked_card_ids(db: AsyncSession, user_id: str) -> set[str]:
    """Cards tied up in a pending offer, on either side of it."""
    offers = await db.scalars(
        select(TradeOffer).where(
            TradeOffer.status == TradeStatus.PENDING,
            (TradeOffer.sender_id == user_id) | (TradeOffer.receiver_id == user_id),
        )
    )
    locked: set[str] = set()
    for offer in offers:
        locked.update(offer.sender_cards or [])
        locked.update(offer.receiver_cards or [])
    return locked


async def squad_card_ids(db: AsyncSession, user_id: str) -> set[str]:
    rows = await db.scalars(select(SquadEntry.user_card_id).where(SquadEntry.user_id == user_id))
    return set(rows)


async def serialize_cards(
    db: AsyncSession,
    cards: Sequence[UserCard],
    *,
    locked: set[str] | None = None,
    in_squad: set[str] | None = None,
) -> list[UserCardOut]:
    templates = await load_templates(db, [(c.card_type, c.card_template_id) for c in cards])
    result: list[UserCardOut] = []
    for card in cards:
        tpl = templates.get((card.card_type, card.card_template_id))
        if tpl is None:
            continue  # template deleted (e.g. player dropped from the tournament)
        result.append(
            UserCardOut(
                id=card.id,
                card_type=card.card_type,
                card_template_id=card.card_template_id,
                acquired_at=card.acquired_at,
                source=card.source,
                locked_by_trade=card.id in (locked or set()),
                in_squad=card.id in (in_squad or set()),
                is_permanent=card.is_permanent,
                tournaments_used=card.tournaments_used,
                runs_left=card.runs_left,
                template=tpl,
            )
        )
    return result
