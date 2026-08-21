from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import Match, MatchStatus, Player, PlayerCardTemplate, Position, Rarity, Team
from app.services.card_service import CardService
from app.services.media import MediaService
from app.services.ratings import RatingService, rarities_for_rank, round_depth, scale

TODAY = date(2026, 8, 21)


async def add_match(db, home: Team, away: Team, *, home_goals, away_goals, digital, physical, round_label, shootouts=(0, 0)):
    match = Match(
        external_id=f"ext-{home.id}-{away.id}-{round_label}",
        slug=f"M{home.id}{away.id}{len(round_label)}",
        tournament_slug="phygital-football-2026",
        home_team_id=home.id,
        away_team_id=away.id,
        status=MatchStatus.COMPLETED,
        home_score=home_goals,
        away_score=away_goals,
        home_digital=digital[0],
        away_digital=digital[1],
        home_physical=physical[0],
        away_physical=physical[1],
        home_shootouts=shootouts[0],
        away_shootouts=shootouts[1],
        winner_team_id=home.id if home_goals > away_goals else (away.id if away_goals > home_goals else None),
        round_label=round_label,
        start_time=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db.add(match)
    await db.commit()
    return match


@pytest.fixture
async def rated(db, world):
    """On top of the fixture match Alpha thrashes Bravo twice and reaches the
    final, so the two sides end up at opposite ends of the table."""
    alpha, bravo = world["teams"]
    await add_match(db, alpha, bravo, home_goals=4, away_goals=0, digital=(2, 0), physical=(2, 0), round_label="Group A. 2nd Round")
    await add_match(db, alpha, bravo, home_goals=3, away_goals=1, digital=(2, 1), physical=(1, 0), round_label="Final")
    result = await RatingService(db, today=TODAY).recompute()
    return result


def test_round_depth_reads_the_bracket_label():
    assert round_depth("Final") == 6
    assert round_depth("2nd SF") == 4
    assert round_depth("Group A. 1st Round") == 1
    assert round_depth(None) == 1


def test_scale_clamps_and_spreads():
    assert scale(0, 0, 10) == 42
    assert scale(10, 0, 10) == 97
    assert scale(-5, 0, 10) == 42
    assert 42 < scale(5, 0, 10) < 97
    # a degenerate range must not blow up
    assert scale(3, 3, 3) == (42 + 97) // 2


def test_rarity_tiers_follow_the_ranking():
    assert rarities_for_rank(1) == ["COMMON", "RARE", "EPIC", "LEGENDARY"]
    assert rarities_for_rank(11) == ["COMMON", "RARE", "EPIC"]
    assert rarities_for_rank(33) == ["COMMON", "RARE"]
    assert rarities_for_rank(120) == ["COMMON"]
    assert rarities_for_rank(None) == ["COMMON"]


async def test_recompute_rates_the_winner_above_the_loser(db, world, rated):
    assert rated["teams"] == 2
    assert rated["players"] == 12

    alpha, bravo = world["teams"]
    await db.refresh(alpha)
    await db.refresh(bravo)

    assert alpha.ovr > bravo.ovr
    assert alpha.rank == 1 and bravo.rank == 2
    # three wins counting the 3:0 already in the fixture
    assert (alpha.wins, alpha.losses) == (3, 0)
    assert (bravo.wins, bravo.losses) == (0, 3)
    assert alpha.goals_for == 10 and alpha.goals_against == 1
    assert alpha.best_round == 6  # reached the final


async def test_every_player_is_ranked_and_ordered(db, world, rated):
    players = list(await db.scalars(select(Player).order_by(Player.rank)))
    ranks = [p.rank for p in players]

    assert ranks == list(range(1, 13))
    assert players[0].ovr >= players[-1].ovr
    # the top of the table belongs to the winning side
    assert players[0].team.title.startswith("Alpha")


async def test_goalkeepers_are_graded_on_defence(db, world, rated):
    keepers = list(await db.scalars(select(Player).where(Player.position == Position.GOALKEEPER)))
    alpha_keeper = next(k for k in keepers if k.team.title.startswith("Alpha"))
    bravo_keeper = next(k for k in keepers if k.team.title.startswith("Bravo"))

    # Alpha conceded one goal in two games, Bravo conceded seven
    assert alpha_keeper.attributes["def"] > bravo_keeper.attributes["def"]
    assert alpha_keeper.ovr > bravo_keeper.ovr


async def test_shirt_numbers_shade_the_attributes(db, world, rated):
    alpha_players = list(
        await db.scalars(select(Player).where(Player.position == Position.FIELD))
    )
    striker = alpha_players[0]
    striker.jersey_number = 10  # an attacking shirt
    plain = alpha_players[1]
    plain.jersey_number = 77
    await db.commit()

    await RatingService(db, today=TODAY).recompute()
    await db.refresh(striker)
    await db.refresh(plain)

    assert striker.attributes["atk"] > plain.attributes["atk"]


async def test_templates_are_minted_by_rank(db, world, rated):
    await db.execute(PlayerCardTemplate.__table__.delete())
    await db.commit()

    created = await CardService(db).ensure_templates()
    assert created > 0

    templates = list(await db.scalars(select(PlayerCardTemplate)))
    by_rarity = {r: 0 for r in Rarity}
    for tpl in templates:
        by_rarity[tpl.rarity] += 1

    # everyone gets a common print, higher tiers are scarce by construction
    assert by_rarity[Rarity.COMMON] == 12
    assert by_rarity[Rarity.LEGENDARY] <= by_rarity[Rarity.EPIC] <= by_rarity[Rarity.RARE]
    assert by_rarity[Rarity.LEGENDARY] > 0


async def test_stronger_cards_cost_more(db, world, rated):
    assert CardService._price(100, 90) > CardService._price(100, 50)
    assert CardService._price(100, 0) == 100


def test_expired_presigned_link_is_retried_bare():
    signed = "https://storage.example.com/bucket/photo.jpeg?X-Amz-Signature=dead&X-Amz-Date=20260722T073401Z"
    assert MediaService.candidate_urls(signed) == [
        "https://storage.example.com/bucket/photo.jpeg",
        signed,
    ]
    plain = "https://storage.example.com/bucket/photo.jpeg"
    assert MediaService.candidate_urls(plain) == [plain]
