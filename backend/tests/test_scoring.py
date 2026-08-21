from __future__ import annotations

from sqlalchemy import select

from app.models import PlayerMatchStat, PointsHistory, PositionSlot, Rarity
from app.services.scoring import ScoringService
from app.services.squad_service import SquadService
from tests.conftest import give_card

ALPHA_GK_COMMON = 1
ALPHA_GK_LEGENDARY = 4
ALPHA_FIELDS = [5, 9, 13, 17]
ALPHA_PLAYER_IDS = [1, 2, 3, 4, 5]
BRAVO_GK = 25


async def field_alpha(db, user, gk_template: int = ALPHA_GK_COMMON) -> SquadService:
    """Alice fields the whole Alpha starting five, which won 3:0."""
    service = SquadService(db)
    card = await give_card(db, user, gk_template)
    await service.select_player(user, card.id, PositionSlot.GK)
    for slot, template in zip(
        (PositionSlot.F1, PositionSlot.F2, PositionSlot.F3, PositionSlot.F4), ALPHA_FIELDS
    ):
        card = await give_card(db, user, template)
        await service.select_player(user, card.id, slot)
    return service


async def test_team_result_alone_produces_points(db, world, alice):
    await field_alpha(db, alice)
    points, breakdown, is_perfect = await ScoringService(db).calculate_match_points(
        alice, world["match"]
    )

    # appearance 2 + win 4 + digital 2 + physical 1 = 9 shared by everyone,
    # plus clean sheet 5 for the keeper and 1 for each field player
    gk = breakdown["players"]["1"]
    assert gk["points"] == 14
    assert breakdown["players"]["2"]["points"] == 10
    assert points == 14 + 10 * 4
    assert is_perfect is False


async def test_captain_doubles_that_player(db, world, alice):
    service = await field_alpha(db, alice)
    entries = await service.get_entries(alice.id)
    await service.set_captain(alice, entries[0].id)  # the goalkeeper

    points, breakdown, _ = await ScoringService(db).calculate_match_points(alice, world["match"])
    assert breakdown["players"]["1"]["captain_multiplier"] == 2.0
    assert breakdown["players"]["1"]["points"] == 28
    assert points == 28 + 10 * 4


async def test_rarity_multiplies_the_same_performance(db, world, alice):
    await field_alpha(db, alice, gk_template=ALPHA_GK_LEGENDARY)
    _, breakdown, _ = await ScoringService(db).calculate_match_points(alice, world["match"])

    assert breakdown["players"]["1"]["rarity"] == Rarity.LEGENDARY.value
    assert breakdown["players"]["1"]["points"] == round(14 * 1.6)


async def test_admin_stats_add_on_top_of_the_team_result(db, world, alice):
    await field_alpha(db, alice)
    db.add(PlayerMatchStat(match_id=world["match"].id, player_id=2, goals=2, assists=1))
    await db.commit()

    _, breakdown, _ = await ScoringService(db).calculate_match_points(alice, world["match"])
    # base 10 + two goals at 5 + one assist at 3
    assert breakdown["players"]["2"]["points"] == 23


async def test_players_outside_the_match_score_nothing(db, world, alice):
    service = SquadService(db)
    card = await give_card(db, alice, BRAVO_GK)
    await service.select_player(alice, card.id, PositionSlot.GK)

    points, breakdown, _ = await ScoringService(db).calculate_match_points(
        alice, world["match"]
    )
    # Bravo did play, so its keeper does score; only unrelated teams score zero
    assert "7" in breakdown["players"]
    assert points == breakdown["players"]["7"]["points"]


async def test_perfect_five_pays_the_bonus(db, world, alice):
    await field_alpha(db, alice)
    match = world["match"]
    match.home_lineup_json = [f"ext-1-{i}" for i in range(5)]
    match.away_lineup_json = [f"ext-2-{i}" for i in range(5)]
    match.lineups_source = "admin"
    await db.commit()

    comparison = await SquadService(db).compare_perfect_five(alice, match.id)
    assert comparison.available
    assert comparison.is_perfect

    points, breakdown, is_perfect = await ScoringService(db).calculate_match_points(alice, match)
    assert is_perfect
    assert breakdown["perfect_five_bonus"] == 20
    assert points == 14 + 10 * 4 + 20


async def test_one_wrong_pick_loses_the_bonus(db, world, alice):
    service = await field_alpha(db, alice)
    match = world["match"]
    match.home_lineup_json = [f"ext-1-{i}" for i in range(5)]
    await db.commit()

    replacement = await give_card(db, alice, 21)  # player 6, on the bench in reality
    await service.select_player(alice, replacement.id, PositionSlot.F4)

    comparison = await SquadService(db).compare_perfect_five(alice, match.id)
    assert comparison.available
    assert not comparison.is_perfect
    assert len(comparison.home_matches) == 4


async def test_perfect_five_is_unavailable_without_lineups(db, world, alice):
    await field_alpha(db, alice)
    comparison = await SquadService(db).compare_perfect_five(alice, world["match"].id)

    assert not comparison.available
    assert not comparison.is_perfect
    assert "не заведены" in comparison.message


async def test_settlement_writes_history_and_user_total(db, world, alice):
    service = await field_alpha(db, alice)
    entries = await service.get_entries(alice.id)
    await service.set_captain(alice, entries[0].id)

    result = await ScoringService(db).settle_match(world["match"].id)
    assert result["users"] == 1

    history = await db.scalar(
        select(PointsHistory).where(PointsHistory.user_id == alice.id)
    )
    await db.refresh(alice)
    assert alice.total_points == 28 + 10 * 4
    assert history is not None
    assert history.points == alice.total_points
    assert history.breakdown["players"]["1"]["captain_multiplier"] == 2.0


async def test_settlement_is_idempotent(db, world, alice):
    await field_alpha(db, alice)
    scoring = ScoringService(db)

    await scoring.settle_match(world["match"].id)
    await db.refresh(alice)
    first_total = alice.total_points

    await scoring.settle_match(world["match"].id, force=True)
    await db.refresh(alice)

    assert alice.total_points == first_total


async def test_resettling_after_a_stat_correction_applies_only_the_delta(db, world, alice):
    await field_alpha(db, alice)
    scoring = ScoringService(db)
    await scoring.settle_match(world["match"].id)
    await db.refresh(alice)
    before = alice.total_points

    db.add(PlayerMatchStat(match_id=world["match"].id, player_id=2, goals=1))
    await db.commit()
    await scoring.settle_match(world["match"].id, force=True)
    await db.refresh(alice)

    assert alice.total_points == before + 5


async def test_unfinished_match_is_not_settled(db, world, alice):
    from app.models import MatchStatus

    await field_alpha(db, alice)
    match = world["match"]
    match.status = MatchStatus.SCHEDULED
    await db.commit()

    result = await ScoringService(db).settle_match(match.id)
    assert "skipped" in result
    await db.refresh(alice)
    assert alice.total_points == 0
