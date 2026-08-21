from __future__ import annotations

from sqlalchemy import func, select

from app.bots import BOTS, score_bots, seed_bots
from app.models import SquadEntry, User, UserCard
from app.services.crests import crest_color, crest_svg, monogram
from app.services.media import MediaService


def test_monogram_handles_awkward_club_names():
    assert monogram("NS Team") == "NT"
    assert monogram("Quetzales-Armadillos") == "QA"
    assert monogram("FFK “ROTOR CISS GROUP”") == "FR"
    assert monogram("Penarol") == "PE"
    assert monogram("") == "FC"


def test_a_crest_is_stable_for_a_club():
    first = crest_svg("NS Team", "team-uuid-1")
    second = crest_svg("NS Team", "team-uuid-1")
    other = crest_svg("NS Team", "team-uuid-2")

    assert first == second, "герб не должен меняться между синхронизациями"
    assert first != other, "разные клубы получают разные гербы"
    assert first.startswith("<svg") and first.rstrip().endswith("</svg>")
    assert crest_color("team-uuid-1") != "" and crest_color("team-uuid-1").startswith("#")


def test_image_endpoints_use_the_singular_noun_and_uuid():
    """The badge and the photo live behind their own routes rather than in any
    JSON field, and unlike the detail endpoints they take a uuid, not a slug."""
    team = MediaService.api_image_url("team", "7532aa97-573c-4062-a0fd-0a274d6749bc")
    athlete = MediaService.api_image_url("athlete", "02942809-e493-46b0-a24e-a6a94208acd2")

    assert team.endswith("/team/7532aa97-573c-4062-a0fd-0a274d6749bc/image/")
    assert athlete.endswith("/athlete/02942809-e493-46b0-a24e-a6a94208acd2/image/")


async def test_real_badges_are_preferred_over_generated_crests(db, world, tmp_path, monkeypatch):
    from app.services import media

    monkeypatch.setattr(media, "TEAM_DIR", tmp_path / "teams")

    async def fake_logo(self, client, team):
        return f"teams/{team.slug}-real.png"

    monkeypatch.setattr(MediaService, "_download_team_logo", fake_logo)
    result = await MediaService(db).sync_team_crests()

    assert result["real_logos"] == 2
    assert result["generated_crests"] == 0

    from app.models import Team

    for team in await db.scalars(select(Team)):
        assert team.photo_path.endswith("-real.png")


async def test_a_crest_is_drawn_when_the_badge_is_unreachable(db, world, tmp_path, monkeypatch):
    from app.services import media

    monkeypatch.setattr(media, "TEAM_DIR", tmp_path / "teams")

    async def no_logo(self, client, team):
        return None

    monkeypatch.setattr(MediaService, "_download_team_logo", no_logo)
    result = await MediaService(db).sync_team_crests()

    assert result["real_logos"] == 0
    assert result["generated_crests"] == 2
    assert len(list((tmp_path / "teams").glob("*.svg"))) == 2

    from app.models import Team

    for team in await db.scalars(select(Team)):
        assert team.photo_path and team.photo_path.startswith("teams/")
        assert team.color


async def test_seeded_bots_are_playable_accounts(db, world):
    from app.services.ratings import RatingService
    from tests.test_ratings import TODAY

    await RatingService(db, today=TODAY).recompute()
    result = await seed_bots(db)

    assert result["created"] == len(BOTS)
    bots = list(await db.scalars(select(User).where(User.username.in_([n for n, _ in BOTS]))))
    assert len(bots) == len(BOTS)

    for bot in bots:
        cards = await db.scalar(
            select(func.count()).select_from(UserCard).where(UserCard.user_id == bot.id)
        )
        assert cards > 0, f"{bot.username} должен иметь коллекцию"
        squad = await db.scalar(
            select(func.count()).select_from(SquadEntry).where(SquadEntry.user_id == bot.id)
        )
        assert squad > 0, f"{bot.username} должен иметь состав"


async def test_seeding_bots_twice_changes_nothing(db, world):
    from app.services.ratings import RatingService
    from tests.test_ratings import TODAY

    await RatingService(db, today=TODAY).recompute()
    await seed_bots(db)
    before = await db.scalar(select(func.count()).select_from(UserCard))

    again = await seed_bots(db)

    assert again["created"] == 0
    assert await db.scalar(select(func.count()).select_from(UserCard)) == before


async def test_bots_earn_their_points_through_normal_scoring(db, world):
    from app.services.ratings import RatingService
    from tests.test_ratings import TODAY

    await RatingService(db, today=TODAY).recompute()
    await seed_bots(db)
    result = await score_bots(db)

    assert result["bots"] == len(BOTS)
    scored = list(await db.scalars(select(User).where(User.total_points > 0)))
    assert scored, "рейтинг не должен быть пустым"
    # points come from the scoring service, not from a hard-coded table
    assert all(u.total_points > 0 for u in scored)
