from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from app.core.exceptions import AlreadyExists, InsufficientFunds, InvalidSquad
from app.models import Player, PlayerCardTemplate, PositionSlot, Team, TournamentEntry
from app.services.bracket import build_bracket, is_knockout
from app.services.ratings import RatingService
from app.services.squad_service import SquadService
from app.services.tournament_service import (
    DrawMachine,
    TournamentService,
    win_probability,
)
from tests.conftest import give_card
from tests.test_ratings import TODAY, add_match

SLUG = "phygital-football-2026"


@pytest.fixture
async def tournament(db, world):
    """A two-round bracket: both sides meet in a group match and then a final."""
    alpha, bravo = world["teams"]
    await add_match(db, alpha, bravo, home_goals=4, away_goals=0, digital=(2, 0), physical=(2, 0), round_label="Group A. 2nd Round")
    await add_match(db, alpha, bravo, home_goals=3, away_goals=1, digital=(2, 1), physical=(1, 0), round_label="Final")
    await RatingService(db, today=TODAY).recompute()
    return world


async def field_squad(db, user, top: bool):
    """Five starters drawn from the strongest or the weakest players available."""
    order = Player.ovr.desc() if top else Player.ovr.asc()
    squads = SquadService(db)
    keeper = await db.scalar(
        select(Player).where(Player.position == "GOALKEEPER").order_by(order).limit(1)
    )
    fields = list(
        await db.scalars(select(Player).where(Player.position == "FIELD").order_by(order).limit(4))
    )
    for slot, player in zip(
        [PositionSlot.GK, PositionSlot.F1, PositionSlot.F2, PositionSlot.F3, PositionSlot.F4],
        [keeper] + fields,
    ):
        tpl = await db.scalar(
            select(PlayerCardTemplate).where(PlayerCardTemplate.player_id == player.id).limit(1)
        )
        card = await give_card(db, user, tpl.id)
        await squads.select_player(user, card.id, slot)
    entries = await squads.get_entries(user.id)
    await squads.set_captain(user, entries[0].id)
    return squads


def test_win_probability_is_symmetric_and_unbiased():
    assert win_probability(75, 75) == 0.5
    assert win_probability(90, 60) + win_probability(60, 90) == pytest.approx(1.0)
    assert win_probability(90, 60) > win_probability(80, 60) > 0.5


def test_knockout_labels_are_recognised():
    assert is_knockout("Final") and is_knockout("1st QF") and is_knockout("3rd place")
    assert is_knockout("4th Last 16") and is_knockout("2nd Decider")
    assert not is_knockout("Group A. 1st Round")


def test_the_draw_matches_its_published_odds():
    """The reported chance must be what actually happens, not a dressed-up bias."""
    wins = sum(1 for i in range(4000) if DrawMachine(f"{i:016x}").wins(80, 76))
    assert wins / 4000 == pytest.approx(win_probability(80, 76), abs=0.03)

    even = sum(1 for i in range(4000) if DrawMachine(f"{i:016x}").wins(70, 70))
    assert even / 4000 == pytest.approx(0.5, abs=0.03)


def test_the_same_seed_replays_identically():
    first = [DrawMachine("cafebabecafebabe").scoreline(85, 70) for _ in range(3)]
    second = [DrawMachine("cafebabecafebabe").scoreline(85, 70) for _ in range(3)]
    assert first == second


async def test_bracket_reproduces_history_when_nobody_is_substituted(db, world, tournament):
    """The strongest guarantee: with no user in the field the engine must
    replay the recorded tournament exactly."""
    bracket = await build_bracket(db, SLUG)
    service = TournamentService(db)

    class Absent:
        id = -1

    log = await service._run_bracket(bracket, Absent(), 0, DrawMachine("0123456789abcdef"))

    assert len(log) == len(bracket.matches)
    assert all(m["source"] == "real" for m in log)
    for played, original in zip(log, bracket.matches):
        assert played["home_score"] == original.real_home_score
        assert played["away_score"] == original.real_away_score
        assert played["winner_key"] == original.real_winner_id


async def test_the_weakest_side_is_the_one_replaced(db, world, tournament, alice):
    weakest = await TournamentService(db).weakest_team(SLUG)
    teams = list(await db.scalars(select(Team).where(Team.matches_played > 0)))

    assert weakest.ovr == min(t.ovr for t in teams)
    assert weakest.title.startswith("Bravo")  # lost every match in the fixture


async def test_squad_must_be_complete_to_enter(db, world, tournament, alice):
    with pytest.raises(InvalidSquad):
        await TournamentService(db).preview(alice, SLUG)


async def test_entry_needs_the_fee(db, world, tournament, alice):
    await field_squad(db, alice, top=True)
    alice.coins = 10
    await db.commit()

    with pytest.raises(InsufficientFunds):
        await TournamentService(db).enter(alice, SLUG)


async def test_preview_names_the_opponent_and_the_odds(db, world, tournament, alice):
    await field_squad(db, alice, top=True)
    preview = await TournamentService(db).preview(alice, SLUG)

    assert preview["squad_ovr"] > 0
    assert len(preview["squad"]) == 5
    assert preview["replaced_team"]["title"].startswith("Bravo")
    assert preview["first_match"]["win_chance"] is not None
    assert 0.0 <= preview["first_match"]["win_chance"] <= 1.0


async def test_a_run_records_the_seed_and_pays_the_boost(db, world, tournament, alice):
    await field_squad(db, alice, top=True)
    alice.coins = 5000
    await db.commit()
    before_points = alice.total_points

    entry = await TournamentService(db).enter(alice, SLUG)

    assert entry.seed and len(entry.seed) == 16
    assert entry.played > 0
    assert entry.stage_index >= 1
    assert entry.coins_awarded >= entry.stage_index * 260
    assert alice.total_points == before_points + entry.points_awarded
    assert alice.coins == 5000 - entry.entry_fee + entry.coins_awarded

    stored = await db.scalar(select(TournamentEntry).where(TournamentEntry.user_id == alice.id))
    assert stored is not None and stored.id == entry.id


async def test_the_boost_grows_with_progression(db, world, tournament, alice, bob):
    """Reward is proportional to how far the squad got, nothing else."""
    await field_squad(db, alice, top=True)
    await field_squad(db, bob, top=False)
    alice.coins = bob.coins = 5000
    await db.commit()

    strong = await TournamentService(db).enter(alice, SLUG)
    weak = await TournamentService(db).enter(bob, SLUG)

    assert strong.squad_ovr > weak.squad_ovr
    if strong.stage_index > weak.stage_index:
        assert strong.coins_awarded > weak.coins_awarded
        assert strong.points_awarded > weak.points_awarded
    assert weak.coins_awarded >= 0


async def test_a_second_run_is_held_back_by_the_cooldown(db, world, tournament, alice):
    await field_squad(db, alice, top=True)
    alice.coins = 5000
    await db.commit()

    await TournamentService(db).enter(alice, SLUG)
    with pytest.raises(AlreadyExists):
        await TournamentService(db).enter(alice, SLUG)


async def test_the_same_seed_reproduces_the_whole_run(db, world, tournament, alice, bob):
    await field_squad(db, alice, top=True)
    await field_squad(db, bob, top=True)
    alice.coins = bob.coins = 5000
    await db.commit()

    first = await TournamentService(db).enter(alice, SLUG, seed="1122334455667788")
    second = await TournamentService(db).enter(bob, SLUG, seed="1122334455667788")

    assert first.stage == second.stage
    assert [(m["home_score"], m["away_score"]) for m in first.run_json] == [
        (m["home_score"], m["away_score"]) for m in second.run_json
    ]


async def test_the_user_can_field_players_of_the_teams_it_faces(db, world, tournament, alice):
    """The same athlete may be both in the collection and in an opposing side."""
    await field_squad(db, alice, top=True)
    alice.coins = 5000
    await db.commit()

    entry = await TournamentService(db).enter(alice, SLUG)
    fielded = {slot["team"] for slot in entry.squad_json}
    faced = {
        m["away"]["name"] if m["home"]["is_user"] else m["home"]["name"]
        for m in entry.run_json
        if m["user_involved"]
    }

    assert fielded & faced, "состав собран из игроков команды, с которой он и играет"


async def run_until(db, user, times: int):
    """Enter the tournament `times` times, ignoring the cooldown."""
    from app.models import TournamentEntry as TE

    service = TournamentService(db)
    entries = []
    for _ in range(times):
        user.coins = 5000
        await db.commit()
        entries.append(await service.enter(user, SLUG))
        # clear the gate so the wear mechanic can be exercised in one test
        for row in await db.scalars(select(TE).where(TE.user_id == user.id)):
            row.created_at = row.created_at.replace(year=2020)
        await db.commit()
    return entries


async def test_a_run_spends_one_life_of_every_fielded_card(db, world, tournament, alice):
    from app.models import UserCard

    await field_squad(db, alice, top=True)
    alice.coins = 5000
    await db.commit()

    await TournamentService(db).enter(alice, SLUG)

    cards = list(await db.scalars(select(UserCard).where(UserCard.user_id == alice.id)))
    assert cards, "карточки не должны исчезнуть после первого турнира"
    assert all(c.tournaments_used == 1 for c in cards)
    assert all(c.runs_left == 5 for c in cards)


async def test_an_ordinary_card_is_gone_after_six_tournaments(db, world, tournament, alice):
    from app.core.constants import TOURNAMENT_LIFESPAN
    from app.models import UserCard

    await field_squad(db, alice, top=True)
    entries = await run_until(db, alice, TOURNAMENT_LIFESPAN)

    left = list(await db.scalars(select(UserCard).where(UserCard.user_id == alice.id)))
    assert left == [], "после шести турниров расходные карточки должны пропасть"
    assert entries[-1].retired_json, "последний прогон обязан сообщить, что сгорело"
    assert len(entries[-1].retired_json) == 5

    squad = await SquadService(db).get_entries(alice.id)
    assert squad == [], "сгоревшие карточки не остаются в составе"


async def test_a_permanent_card_never_wears_out(db, world, tournament, alice):
    from app.core.constants import TOURNAMENT_LIFESPAN
    from app.models import UserCard

    await field_squad(db, alice, top=True)
    for card in await db.scalars(select(UserCard).where(UserCard.user_id == alice.id)):
        card.is_permanent = True
    await db.commit()

    await run_until(db, alice, TOURNAMENT_LIFESPAN + 2)

    left = list(await db.scalars(select(UserCard).where(UserCard.user_id == alice.id)))
    assert len(left) == 5, "вечные карточки не сгорают"
    assert all(c.runs_left is None for c in left)
    assert len(await SquadService(db).get_entries(alice.id)) == 5


async def test_the_fifth_run_still_leaves_one_life(db, world, tournament, alice):
    from app.models import UserCard

    await field_squad(db, alice, top=True)
    await run_until(db, alice, 5)

    left = list(await db.scalars(select(UserCard).where(UserCard.user_id == alice.id)))
    assert len(left) == 5
    assert all(c.runs_left == 1 for c in left)
