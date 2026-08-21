from __future__ import annotations

import pytest

from app.core.exceptions import (
    AlreadyExists,
    CardLocked,
    InsufficientFunds,
    NotAllowed,
    NotOwner,
)
from app.models import PositionSlot, TradeStatus, UserCard
from app.services.squad_service import SquadService
from app.services.trade_service import TradeService
from tests.conftest import give_card


async def test_accept_moves_cards_both_ways(db, world, alice, bob):
    a_card = await give_card(db, alice, 5)
    b_card = await give_card(db, bob, 9)
    service = TradeService(db)

    offer = await service.create_offer(alice, bob.id, [a_card.id], [b_card.id])
    accepted = await service.accept_offer(offer.id, bob)

    assert accepted.status == TradeStatus.ACCEPTED
    assert (await db.get(UserCard, a_card.id)).user_id == bob.id
    assert (await db.get(UserCard, b_card.id)).user_id == alice.id


async def test_cannot_offer_a_card_you_do_not_own(db, world, alice, bob):
    b_card = await give_card(db, bob, 9)
    with pytest.raises(NotOwner):
        await TradeService(db).create_offer(alice, bob.id, [b_card.id], [])


async def test_card_cannot_sit_in_two_pending_offers(db, world, alice, bob):
    a_card = await give_card(db, alice, 5)
    service = TradeService(db)
    await service.create_offer(alice, bob.id, [a_card.id], [])

    with pytest.raises(CardLocked):
        await service.create_offer(alice, bob.id, [a_card.id], [])


async def test_only_receiver_may_accept(db, world, alice, bob):
    a_card = await give_card(db, alice, 5)
    service = TradeService(db)
    offer = await service.create_offer(alice, bob.id, [a_card.id], [])

    with pytest.raises(NotAllowed):
        await service.accept_offer(offer.id, alice)


async def test_offer_cannot_be_processed_twice(db, world, alice, bob):
    a_card = await give_card(db, alice, 5)
    service = TradeService(db)
    offer = await service.create_offer(alice, bob.id, [a_card.id], [])
    await service.accept_offer(offer.id, bob)

    with pytest.raises(AlreadyExists):
        await service.decline_offer(offer.id, bob)


async def test_coins_move_with_the_cards(db, world, alice, bob):
    b_card = await give_card(db, bob, 9)
    alice.coins = 500
    bob.coins = 0
    await db.commit()

    service = TradeService(db)
    offer = await service.create_offer(alice, bob.id, [], [b_card.id], sender_coins=300)
    await service.accept_offer(offer.id, bob)

    assert alice.coins == 200
    assert bob.coins == 300


async def test_offer_beyond_your_wallet_is_refused(db, world, alice, bob):
    alice.coins = 50
    await db.commit()
    with pytest.raises(InsufficientFunds):
        await TradeService(db).create_offer(alice, bob.id, [], [], sender_coins=100)


async def test_counter_releases_the_original_lock(db, world, alice, bob):
    a_card = await give_card(db, alice, 5)
    b_card = await give_card(db, bob, 9)
    service = TradeService(db)

    original = await service.create_offer(alice, bob.id, [a_card.id], [b_card.id])
    counter = await service.counter_offer(original.id, bob, [b_card.id], [a_card.id])

    await db.refresh(original)
    assert original.status == TradeStatus.COUNTERED
    assert counter.sender_id == bob.id
    assert counter.counter_of_id == original.id

    await service.accept_offer(counter.id, alice)
    assert (await db.get(UserCard, b_card.id)).user_id == alice.id


async def test_traded_card_leaves_the_previous_squad(db, world, alice, bob):
    """A card that changes hands must not keep occupying the old owner squad."""
    gk_template = 1  # first template of the first goalkeeper
    card = await give_card(db, alice, gk_template)
    await SquadService(db).select_player(alice, card.id, PositionSlot.GK)

    service = TradeService(db)
    offer = await service.create_offer(alice, bob.id, [card.id], [])
    await service.accept_offer(offer.id, bob)

    assert await SquadService(db).get_entries(alice.id) == []


async def test_self_trade_is_rejected(db, world, alice):
    with pytest.raises(NotAllowed):
        await TradeService(db).create_offer(alice, alice.id, [], [], sender_coins=10)
