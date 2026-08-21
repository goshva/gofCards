from __future__ import annotations

import pytest

from app.core.exceptions import InvalidSquad, NotOwner, SquadLocked
from app.models import CardType, MatchStatus, PositionSlot
from app.services.squad_service import SquadService
from tests.conftest import give_card

# Fixture layout: player N owns templates 4*(N-1)+1 .. 4*N, COMMON first.
ALPHA_GK = 1  # player 1, COMMON
ALPHA_FIELDS = [5, 9, 13, 17]  # players 2..5, COMMON
ALPHA_BENCH = 21  # player 6, COMMON, outside the starting five
BRAVO_GK = 25  # player 7, COMMON


async def build_five(db, user, slots_only: bool = False) -> SquadService:
    service = SquadService(db)
    card = await give_card(db, user, ALPHA_GK)
    await service.select_player(user, card.id, PositionSlot.GK)
    for slot, template in zip(
        (PositionSlot.F1, PositionSlot.F2, PositionSlot.F3, PositionSlot.F4), ALPHA_FIELDS
    ):
        card = await give_card(db, user, template)
        await service.select_player(user, card.id, slot)
    return service


async def test_goalkeeper_slot_rejects_a_field_player(db, world, alice):
    card = await give_card(db, alice, ALPHA_FIELDS[0])
    with pytest.raises(InvalidSquad):
        await SquadService(db).select_player(alice, card.id, PositionSlot.GK)


async def test_field_slot_rejects_a_goalkeeper(db, world, alice):
    card = await give_card(db, alice, ALPHA_GK)
    with pytest.raises(InvalidSquad):
        await SquadService(db).select_player(alice, card.id, PositionSlot.F1)


async def test_cannot_field_someone_else_card(db, world, alice, bob):
    card = await give_card(db, bob, ALPHA_GK)
    with pytest.raises(NotOwner):
        await SquadService(db).select_player(alice, card.id, PositionSlot.GK)


async def test_team_cards_cannot_enter_a_squad(db, world, alice):
    card = await give_card(db, alice, 1, CardType.TEAM)
    with pytest.raises(InvalidSquad):
        await SquadService(db).select_player(alice, card.id, PositionSlot.F1)


async def test_same_player_cannot_take_two_slots(db, world, alice):
    service = SquadService(db)
    first = await give_card(db, alice, ALPHA_FIELDS[0])
    second = await give_card(db, alice, ALPHA_FIELDS[0])
    await service.select_player(alice, first.id, PositionSlot.F1)

    with pytest.raises(InvalidSquad):
        await service.select_player(alice, second.id, PositionSlot.F2)


async def test_incomplete_squad_reports_every_gap(db, world, alice):
    card = await give_card(db, alice, ALPHA_GK)
    service = SquadService(db)
    await service.select_player(alice, card.id, PositionSlot.GK)

    result = await service.validate(alice)
    assert not result.valid
    assert {i.code for i in result.issues} >= {"empty_slot", "no_captain"}


async def test_complete_squad_with_captain_is_valid(db, world, alice):
    service = await build_five(db, alice)
    entries = await service.get_entries(alice.id)
    await service.set_captain(alice, entries[0].id)

    result = await service.validate(alice)
    assert result.valid, result.message
    assert result.issues == []


async def test_captain_must_be_a_starter(db, world, alice):
    service = await build_five(db, alice)
    sub = await give_card(db, alice, ALPHA_BENCH)
    entry = await service.select_player(alice, sub.id, PositionSlot.SUB1)

    with pytest.raises(InvalidSquad):
        await service.set_captain(alice, entry.id)


async def test_captaincy_is_exclusive(db, world, alice):
    service = await build_five(db, alice)
    entries = await service.get_entries(alice.id)
    await service.set_captain(alice, entries[0].id)
    await service.set_captain(alice, entries[1].id)

    entries = await service.get_entries(alice.id)
    assert sum(1 for e in entries if e.is_captain) == 1
    assert entries[1].is_captain


async def test_selecting_into_a_taken_slot_replaces_and_keeps_the_armband(db, world, alice):
    service = await build_five(db, alice)
    entries = await service.get_entries(alice.id)
    await service.set_captain(alice, entries[1].id)  # F1

    replacement = await give_card(db, alice, ALPHA_BENCH)
    await service.select_player(alice, replacement.id, PositionSlot.F1)

    entries = await service.get_entries(alice.id)
    f1 = next(e for e in entries if e.position_slot == PositionSlot.F1)
    assert f1.is_captain
    assert len(entries) == 5
