"""Small operational CLI: python -m scripts.manage <command>."""
from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.db import SessionLocal, engine
from app.core.security import hash_password
from app.models import Base, User, UserRole
from app.seed import seed_packs
from app.services.scoring import ScoringService
from app.services.sync_service import run_sync_once


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        created = await seed_packs(db)
    print(f"tables ready, packs seeded: {created}")


async def sync() -> None:
    await create_tables()
    print(await run_sync_once())


async def settle() -> None:
    async with SessionLocal() as db:
        print(await ScoringService(db).settle_pending())


async def make_admin(username: str) -> None:
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.username == username))
        if user is None:
            print(f"no such user: {username}")
            return
        user.role = UserRole.ADMIN
        await db.commit()
        print(f"{username} is now an admin")


async def create_admin(username: str, email: str, password: str) -> None:
    await create_tables()
    async with SessionLocal() as db:
        if await db.scalar(select(User).where(User.username == username)):
            print("user already exists")
            return
        db.add(
            User(
                username=username,
                email=email.lower(),
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
            )
        )
        await db.commit()
        print(f"admin created: {username}")


async def seed_bots_cmd() -> None:
    from app.bots import score_bots, seed_bots

    async with SessionLocal() as db:
        print(await seed_bots(db))
        print(await score_bots(db))


async def crests() -> None:
    from app.services.media import MediaService

    async with SessionLocal() as db:
        print(await MediaService(db).sync_team_crests(force=True))


async def add_coins(username: str, amount: str) -> None:
    """Top up a wallet. A negative amount takes coins away."""
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.username == username))
        if user is None:
            print(f"no such user: {username}")
            return
        before = user.coins
        user.coins = max(0, user.coins + int(amount))
        await db.commit()
        print(f"{username}: {before} -> {user.coins} coins")


COMMANDS = {
    "init": create_tables,
    "sync": sync,
    "settle": settle,
    "make-admin": make_admin,
    "add-coins": add_coins,
    "seed-bots": seed_bots_cmd,
    "crests": crests,
    "create-admin": create_admin,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("commands: " + ", ".join(COMMANDS))
        raise SystemExit(1)
    asyncio.run(COMMANDS[sys.argv[1]](*sys.argv[2:]))


if __name__ == "__main__":
    main()
