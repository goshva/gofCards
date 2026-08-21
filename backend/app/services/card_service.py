from __future__ import annotations

import random
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import RARITY_BASE_PRICE, RARITY_WEIGHTS
from app.core.exceptions import InsufficientFunds, NotFound
from app.models import (
    CardType,
    Pack,
    PackOpening,
    Player,
    PlayerCardTemplate,
    Rarity,
    Team,
    TeamCardTemplate,
    User,
    UserCard,
)
from app.schemas.card import UserCardOut
from app.services import catalog
from app.services.ratings import rarities_for_rank


class CardService:
    def __init__(self, db: AsyncSession, rng: random.Random | None = None) -> None:
        self.db = db
        self.rng = rng or random.Random()

    @staticmethod
    def _price(base: int, ovr: int) -> int:
        """A stronger card costs more, so the market reflects the ranking."""
        if not ovr:
            return base
        return max(10, int(round(base * (0.55 + ovr / 100))))

    async def ensure_templates(self) -> int:
        """Mint the card templates.

        Which rarities a player exists in follows their rank, so a legendary
        card is genuinely one of the ten best athletes of the tournament rather
        than a lucky roll on a nobody. Everyone has a common print.
        """
        created = 0
        players = list(await self.db.scalars(select(Player)))
        existing_player = {
            (row.player_id, row.rarity) for row in await self.db.scalars(select(PlayerCardTemplate))
        }
        for player in players:
            for name in rarities_for_rank(player.rank):
                rarity = Rarity(name)
                if (player.id, rarity) in existing_player:
                    continue
                self.db.add(
                    PlayerCardTemplate(
                        player_id=player.id,
                        rarity=rarity,
                        base_price=self._price(RARITY_BASE_PRICE[name], player.ovr),
                        image_url=player.image_url,
                    )
                )
                created += 1

        teams = list(await self.db.scalars(select(Team)))
        existing_team = {
            (row.team_id, row.rarity) for row in await self.db.scalars(select(TeamCardTemplate))
        }
        for team in teams:
            for rarity in Rarity:
                if (team.id, rarity) in existing_team:
                    continue
                self.db.add(
                    TeamCardTemplate(
                        team_id=team.id,
                        rarity=rarity,
                        base_price=self._price(RARITY_BASE_PRICE[rarity.value] * 2, team.ovr),
                        image_url=team.image_url,
                    )
                )
                created += 1

        await self.db.commit()
        return created

    async def refresh_template_images(self) -> int:
        """Point templates at the locally mirrored photo, falling back to the
        upstream presigned link while the download has not happened yet."""
        updated = 0
        for tpl in await self.db.scalars(select(PlayerCardTemplate)):
            player = tpl.player
            if not player:
                continue
            wanted = f"/media/{player.photo_path}" if player.photo_path else player.image_url
            if wanted and tpl.image_url != wanted:
                tpl.image_url = wanted
                updated += 1
        for tpl in await self.db.scalars(select(TeamCardTemplate)):
            if tpl.team and tpl.team.image_url and tpl.image_url != tpl.team.image_url:
                tpl.image_url = tpl.team.image_url
                updated += 1
        await self.db.commit()
        return updated

    def _roll_rarity(self, odds: dict[str, int] | None) -> Rarity:
        weights = dict(RARITY_WEIGHTS)
        if odds:
            weights.update(odds)
        names = [r.value for r in Rarity if weights.get(r.value, 0) > 0]
        if not names:
            return Rarity.COMMON
        picked = self.rng.choices(names, weights=[weights[n] for n in names], k=1)[0]
        return Rarity(picked)

    async def _random_player_template(self, rarity: Rarity) -> PlayerCardTemplate | None:
        ids = list(
            await self.db.scalars(
                select(PlayerCardTemplate.id).where(PlayerCardTemplate.rarity == rarity)
            )
        )
        if not ids:
            return None
        return await self.db.get(PlayerCardTemplate, self.rng.choice(ids))

    async def _random_team_template(self, rarity: Rarity) -> TeamCardTemplate | None:
        ids = list(
            await self.db.scalars(
                select(TeamCardTemplate.id).where(TeamCardTemplate.rarity == rarity)
            )
        )
        if not ids:
            return None
        return await self.db.get(TeamCardTemplate, self.rng.choice(ids))

    async def _draw_one(self, rarity: Rarity, team_card_chance: int) -> UserCard | None:
        tpl = None
        if self.rng.randint(1, 100) <= team_card_chance:
            tpl = await self._random_team_template(rarity)
        if tpl is None:
            tpl = await self._random_player_template(rarity)
        if tpl is None:
            for fallback in Rarity:
                tpl = await self._random_player_template(fallback)
                if tpl is not None:
                    break
        if tpl is None:
            return None
        return UserCard(card_template_id=tpl.id, card_type=tpl.card_type)

    async def _goalkeeper_template_ids(self, rarity: Rarity | None = None) -> list[int]:
        stmt = (
            select(PlayerCardTemplate.id)
            .join(Player, Player.id == PlayerCardTemplate.player_id)
            .where(Player.position == "GOALKEEPER")
        )
        if rarity is not None:
            stmt = stmt.where(PlayerCardTemplate.rarity == rarity)
        return list(await self.db.scalars(stmt))

    async def _contains_goalkeeper(self, cards: list[UserCard]) -> bool:
        player_cards = [c for c in cards if c.card_type == CardType.PLAYER]
        if not player_cards:
            return False
        keeper_ids = set(await self._goalkeeper_template_ids())
        return any(c.card_template_id in keeper_ids for c in player_cards)

    async def _draw_goalkeeper(self) -> UserCard | None:
        """Used by the starter booster so a new account can always field a squad."""
        for rarity in Rarity:
            ids = await self._goalkeeper_template_ids(rarity)
            if ids:
                return UserCard(
                    card_template_id=self.rng.choice(ids), card_type=CardType.PLAYER
                )
        return None

    async def open_pack(self, user: User, pack: Pack) -> tuple[PackOpening, list[UserCard]]:
        if not pack.is_active:
            raise NotFound("Бустер недоступен")
        if user.coins < pack.price:
            raise InsufficientFunds(f"Нужно {pack.price} монет, доступно {user.coins}")

        drawn: list[UserCard] = []
        for rarity_key, count in (pack.contents_json or {}).items():
            for _ in range(int(count)):
                rarity = (
                    self._roll_rarity(pack.odds_json)
                    if rarity_key.upper() == "ANY"
                    else Rarity(rarity_key.upper())
                )
                card = await self._draw_one(rarity, pack.team_card_chance)
                if card is not None:
                    drawn.append(card)

        if pack.guarantees_goalkeeper and not await self._contains_goalkeeper(drawn):
            keeper = await self._draw_goalkeeper()
            if keeper is not None and drawn:
                # swap the last pull rather than adding a sixth card
                drawn[-1] = keeper
            elif keeper is not None:
                drawn.append(keeper)

        if not drawn:
            raise NotFound("Каталог карточек пуст, сначала выполните синхронизацию")

        for card in drawn:
            card.user_id = user.id
            card.source = "collector" if pack.grants_permanent else "pack"
            card.is_permanent = pack.grants_permanent
            self.db.add(card)

        user.coins -= pack.price
        opening = PackOpening(
            user_id=user.id,
            pack_id=pack.id,
            coins_spent=pack.price,
            cards_received=[
                {
                    "card_type": c.card_type.value,
                    "card_template_id": c.card_template_id,
                    "is_permanent": c.is_permanent,
                }
                for c in drawn
            ],
        )
        self.db.add(opening)
        await self.db.commit()
        for card in drawn:
            await self.db.refresh(card)
        return opening, drawn

    async def collection_stats(self, user_id: str) -> dict:
        cards = list(await self.db.scalars(select(UserCard).where(UserCard.user_id == user_id)))
        templates = await catalog.load_templates(
            self.db, [(c.card_type, c.card_template_id) for c in cards]
        )
        by_rarity: dict[str, int] = {r.value: 0 for r in Rarity}
        for card in cards:
            tpl = templates.get((card.card_type, card.card_template_id))
            if tpl:
                by_rarity[tpl.rarity.value] += 1
        total_templates = (
            await self.db.scalar(select(func.count()).select_from(PlayerCardTemplate)) or 0
        ) + (await self.db.scalar(select(func.count()).select_from(TeamCardTemplate)) or 0)
        ovrs = [
            tpl.ovr
            for card in cards
            if (tpl := templates.get((card.card_type, card.card_template_id))) and tpl.ovr
        ]
        return {
            "total_cards": len(cards),
            "unique_templates": len({(c.card_type, c.card_template_id) for c in cards}),
            "by_rarity": by_rarity,
            "player_cards": sum(1 for c in cards if c.card_type == CardType.PLAYER),
            "team_cards": sum(1 for c in cards if c.card_type == CardType.TEAM),
            "templates_total": total_templates,
            "best_ovr": max(ovrs, default=0),
            "average_ovr": round(sum(ovrs) / len(ovrs), 1) if ovrs else 0.0,
        }

    async def serialize(self, user_id: str, cards: Sequence[UserCard]) -> list[UserCardOut]:
        return await catalog.serialize_cards(
            self.db,
            cards,
            locked=await catalog.locked_card_ids(self.db, user_id),
            in_squad=await catalog.squad_card_ids(self.db, user_id),
        )
