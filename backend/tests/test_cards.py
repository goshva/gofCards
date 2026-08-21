from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.core.constants import TOURNAMENT_LIFESPAN
from app.core.exceptions import InsufficientFunds
from app.models import CardType, Pack, PlayerCardTemplate, Rarity, UserCard
from app.services.card_service import CardService


async def test_ensure_templates_covers_every_rarity(db, world):
    created = await CardService(db).ensure_templates()
    assert created == 0  # the fixture already minted them

    per_player = await db.scalar(
        select(func.count()).select_from(PlayerCardTemplate).where(PlayerCardTemplate.player_id == 1)
    )
    assert per_player == len(Rarity)


async def test_open_pack_draws_cards_and_charges_coins(db, world, alice, rng):
    pack = await db.get(Pack, 1)
    alice.coins = 500
    await db.commit()

    opening, cards = await CardService(db, rng).open_pack(alice, pack)

    assert len(cards) == 5  # 3 COMMON + 2 ANY
    assert alice.coins == 400
    assert opening.coins_spent == 100
    assert len(opening.cards_received) == 5
    owned = await db.scalar(
        select(func.count()).select_from(UserCard).where(UserCard.user_id == alice.id)
    )
    assert owned == 5


async def test_open_pack_respects_declared_rarities(db, world, alice, rng):
    pack = await db.get(Pack, 1)
    _, cards = await CardService(db, rng).open_pack(alice, pack)

    templates = await CardService(db).serialize(alice.id, cards)
    commons = [c for c in templates if c.template.rarity == Rarity.COMMON]
    assert len(commons) >= 3


async def test_open_pack_rejects_broke_user(db, world, alice, rng):
    pack = await db.get(Pack, 1)
    alice.coins = 10
    await db.commit()

    with pytest.raises(InsufficientFunds):
        await CardService(db, rng).open_pack(alice, pack)

    assert alice.coins == 10


async def test_rarity_roll_follows_weights(db, rng):
    service = CardService(db, rng)
    rolls = [service._roll_rarity(None).value for _ in range(2000)]
    assert rolls.count("COMMON") > rolls.count("RARE") > rolls.count("EPIC")
    assert rolls.count("LEGENDARY") < rolls.count("EPIC")


async def test_starter_booster_always_yields_a_goalkeeper(db, world, alice, rng):
    """Players are bought, not given — but the cheapest booster must keep a
    legal squad reachable, so it guarantees a keeper."""
    pack = await db.get(Pack, 1)
    pack.guarantees_goalkeeper = True
    await db.commit()

    for _ in range(6):
        alice.coins = 500
        await db.commit()
        _, cards = await CardService(db, rng).open_pack(alice, pack)
        serialized = await CardService(db).serialize(alice.id, cards)
        keepers = [
            c
            for c in serialized
            if c.template.position is not None and c.template.position.value == "GOALKEEPER"
        ]
        assert keepers, "стартовый бустер обязан содержать вратаря"


async def test_collector_booster_mints_permanent_cards(db, world, alice, rng):
    pack = await db.get(Pack, 1)
    pack.grants_permanent = True
    await db.commit()
    alice.coins = 500
    await db.commit()

    _, cards = await CardService(db, rng).open_pack(alice, pack)

    assert cards and all(c.is_permanent for c in cards)
    assert all(c.runs_left is None for c in cards)
    assert all(c.source == "collector" for c in cards)


async def test_ordinary_cards_start_with_a_full_lifespan(db, world, alice, rng):
    pack = await db.get(Pack, 1)
    alice.coins = 500
    await db.commit()

    _, cards = await CardService(db, rng).open_pack(alice, pack)

    assert all(not c.is_permanent for c in cards)
    assert all(c.runs_left == TOURNAMENT_LIFESPAN for c in cards)


async def test_collection_stats_counts_by_rarity(db, world, alice, rng):
    pack = await db.get(Pack, 1)
    alice.coins = 500
    await db.commit()
    _, cards = await CardService(db, rng).open_pack(alice, pack)
    stats = await CardService(db).collection_stats(alice.id)

    assert stats["total_cards"] == len(cards)
    assert sum(stats["by_rarity"].values()) == len(cards)
    assert stats["player_cards"] + stats["team_cards"] == len(cards)
    assert stats["templates_total"] == 56  # 12 players + 2 teams, four rarities each
