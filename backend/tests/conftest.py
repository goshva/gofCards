from __future__ import annotations

import random
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.constants import RARITY_BASE_PRICE
from app.core.security import hash_password
from app.models import (
    Base,
    CardType,
    Match,
    MatchStatus,
    Pack,
    Player,
    PlayerCardTemplate,
    Position,
    Rarity,
    Team,
    TeamCardTemplate,
    User,
    UserCard,
)


@pytest.fixture
async def db() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def rng() -> random.Random:
    return random.Random(1337)


@pytest.fixture
async def world(db: AsyncSession) -> dict:
    """Two teams of one goalkeeper plus five field players, one finished match,
    templates in every rarity. Mirrors the real phygital football shape."""
    teams = []
    players: dict[str, list[Player]] = {}
    for t_idx, name in enumerate(("Alpha", "Bravo"), start=1):
        team = Team(external_id=f"ext-team-{t_idx}", slug=f"team-{t_idx}", title=f"{name} Team")
        db.add(team)
        await db.flush()
        teams.append(team)
        roster = []
        for p_idx in range(6):
            position = Position.GOALKEEPER if p_idx == 0 else Position.FIELD
            player = Player(
                external_id=f"ext-{t_idx}-{p_idx}",
                slug=f"p-{t_idx}-{p_idx}",
                nickname=f"{name}{p_idx}",
                position=position,
                team_id=team.id,
            )
            db.add(player)
            roster.append(player)
        await db.flush()
        players[name] = roster

    for roster in players.values():
        for player in roster:
            for rarity in Rarity:
                db.add(
                    PlayerCardTemplate(
                        player_id=player.id, rarity=rarity, base_price=RARITY_BASE_PRICE[rarity.value]
                    )
                )
    for team in teams:
        for rarity in Rarity:
            db.add(
                TeamCardTemplate(
                    team_id=team.id, rarity=rarity, base_price=RARITY_BASE_PRICE[rarity.value] * 2
                )
            )

    match = Match(
        external_id="ext-match-1",
        slug="M1",
        tournament_slug="phygital-football-2026",
        home_team_id=teams[0].id,
        away_team_id=teams[1].id,
        status=MatchStatus.COMPLETED,
        home_score=3,
        away_score=0,
        home_digital=2,
        away_digital=0,
        home_physical=1,
        away_physical=0,
        winner_team_id=teams[0].id,
        start_time=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db.add(match)
    db.add(
        Pack(
            id=1,
            name="Test pack",
            price=100,
            contents_json={"COMMON": 3, "ANY": 2},
            team_card_chance=10,
        )
    )
    await db.commit()
    await db.refresh(match)
    return {"teams": teams, "players": players, "match": match}


@pytest.fixture
async def alice(db: AsyncSession) -> User:
    user = User(username="alice", email="alice@example.com", password_hash=hash_password("password1"))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def bob(db: AsyncSession) -> User:
    user = User(username="bob", email="bob@example.com", password_hash=hash_password("password1"))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def give_card(db: AsyncSession, user: User, template_id: int, card_type: CardType = CardType.PLAYER) -> UserCard:
    card = UserCard(user_id=user.id, card_template_id=template_id, card_type=card_type, source="admin")
    db.add(card)
    await db.commit()
    await db.refresh(card)
    return card
