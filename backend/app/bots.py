"""Pre-created accounts so the leaderboard is populated from day one.

They are ordinary users with a role of USER, a real collection and a real
squad — the ranking screen shows them exactly like anyone else. Their points
come from actual scoring runs, not from a hard-coded number.
"""
from __future__ import annotations

import random

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import SQUAD_RULES
from app.core.security import hash_password
from app.models import (
    CardType,
    Player,
    PlayerCardTemplate,
    Position,
    PositionSlot,
    Rarity,
    User,
    UserCard,
)
from app.services.squad_service import SquadService

BOTS: list[tuple[str, int]] = [
    ("Astana_Falcons", 92),
    ("phygital_pro", 88),
    ("KZ_Manager", 84),
    ("DigitalStriker", 80),
    ("Samruk_Fan", 76),
    ("MetaKeeper", 72),
    ("BraveDrone", 68),
    ("SteppeUnited", 64),
    ("RookieCollector", 58),
    ("CasualPlayer", 52),
]

STARTING_SLOTS = [PositionSlot(s) for s in SQUAD_RULES["startingSlots"]]


async def _pick_templates(db: AsyncSession, rng: random.Random, strength: int) -> list[PlayerCardTemplate]:
    """Stronger bots draw from the top of the ranking, weaker ones from lower down."""
    total = await db.scalar(select(func.count()).select_from(Player).where(Player.rank.isnot(None))) or 0
    if not total:
        return []

    window = max(12, int(total * 0.35))
    top = max(0, int((100 - strength) / 100 * (total - window)))

    async def one(position: Position) -> PlayerCardTemplate | None:
        players = list(
            await db.scalars(
                select(Player)
                .where(Player.position == position, Player.rank.isnot(None))
                .order_by(Player.rank)
                .offset(top)
                .limit(window)
            )
        )
        if not players:
            players = list(
                await db.scalars(select(Player).where(Player.position == position).limit(window))
            )
        if not players:
            return None
        player = rng.choice(players)
        options = list(
            await db.scalars(
                select(PlayerCardTemplate).where(PlayerCardTemplate.player_id == player.id)
            )
        )
        return rng.choice(options) if options else None

    picked: list[PlayerCardTemplate] = []
    keeper = await one(Position.GOALKEEPER)
    if keeper:
        picked.append(keeper)
    seen = {keeper.player_id} if keeper else set()
    attempts = 0
    while len(picked) < len(STARTING_SLOTS) and attempts < 40:
        attempts += 1
        field = await one(Position.FIELD)
        if field and field.player_id not in seen:
            seen.add(field.player_id)
            picked.append(field)
    return picked


async def seed_bots(db: AsyncSession, seed: int = 20260821) -> dict:
    """Idempotent: an existing bot keeps its collection and its points."""
    rng = random.Random(seed)
    squads = SquadService(db)
    created = 0

    for username, strength in BOTS:
        existing = await db.scalar(select(User).where(User.username == username))
        if existing is not None:
            continue

        user = User(
            username=username,
            email=f"{username.lower()}@bots.gofcards.local",
            password_hash=hash_password(f"bot-{rng.getrandbits(48):012x}"),
            coins=rng.randint(300, 2500),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        templates = await _pick_templates(db, rng, strength)
        for index, template in enumerate(templates):
            card = UserCard(
                user_id=user.id,
                card_template_id=template.id,
                card_type=CardType.PLAYER,
                source="bot",
                # a couple of bots have already invested in collector cards
                is_permanent=strength >= 84 and index < 2,
                tournaments_used=rng.randint(0, 4),
            )
            db.add(card)
            await db.commit()
            await db.refresh(card)
            if index < len(STARTING_SLOTS):
                await squads.select_player(user, card.id, STARTING_SLOTS[index])

        # a few spare cards so their collection does not look bare
        spares = list(await db.scalars(select(PlayerCardTemplate).order_by(func.random()).limit(rng.randint(2, 6))))
        for template in spares:
            db.add(
                UserCard(
                    user_id=user.id,
                    card_template_id=template.id,
                    card_type=CardType.PLAYER,
                    source="bot",
                    tournaments_used=rng.randint(0, 5),
                )
            )

        entries = await squads.get_entries(user.id)
        if entries:
            await squads.set_captain(user, entries[0].id)
        await db.commit()
        created += 1

    return {"created": created, "total": len(BOTS)}


async def score_bots(db: AsyncSession) -> dict:
    """Run the normal scoring over every finished match for the bot accounts.

    Points are earned the same way a player earns them, so the ranking is
    comparable rather than decorative.
    """
    from app.models import Match, MatchStatus
    from app.services.scoring import ScoringService

    scoring = ScoringService(db)
    names = [name for name, _ in BOTS]
    bots = list(await db.scalars(select(User).where(User.username.in_(names))))
    matches = list(
        await db.scalars(
            select(Match).where(Match.status == MatchStatus.COMPLETED).order_by(Match.round)
        )
    )

    scored = 0
    for bot in bots:
        for match in matches:
            points, breakdown, is_perfect = await scoring.calculate_match_points(bot, match)
            if points:
                bot.total_points += points
                scored += 1
    await db.commit()
    return {"bots": len(bots), "awards": scored}
