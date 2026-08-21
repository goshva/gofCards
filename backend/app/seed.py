from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Pack

DEFAULT_PACKS = [
    {
        "id": 1,
        "name": "Стартовый бустер",
        "description": "5 карточек, вратарь гарантирован. Ресурс — 6 турниров",
        "price": 200,
        "contents_json": {"COMMON": 4, "ANY": 1},
        "odds_json": None,
        "team_card_chance": 8,
        "grants_permanent": False,
        "guarantees_goalkeeper": True,
    },
    {
        "id": 2,
        "name": "Премиум бустер",
        "description": "5 карточек, гарантирована минимум одна редкая",
        "price": 600,
        "contents_json": {"COMMON": 2, "RARE": 1, "ANY": 2},
        "odds_json": {"COMMON": 40, "RARE": 40, "EPIC": 15, "LEGENDARY": 5},
        "team_card_chance": 12,
        "grants_permanent": False,
        "guarantees_goalkeeper": False,
    },
    {
        "id": 3,
        "name": "Легендарный бустер",
        "description": "3 карточки с резко повышенным шансом на эпик и легенду",
        "price": 1500,
        "contents_json": {"RARE": 1, "ANY": 2},
        "odds_json": {"COMMON": 10, "RARE": 35, "EPIC": 35, "LEGENDARY": 20},
        "team_card_chance": 20,
        "grants_permanent": False,
        "guarantees_goalkeeper": False,
    },
    {
        "id": 4,
        "name": "Коллекционный бустер",
        "description": "3 карточки, которые НЕ изнашиваются — остаются навсегда",
        "price": 3500,
        "contents_json": {"RARE": 1, "ANY": 2},
        "odds_json": {"COMMON": 0, "RARE": 30, "EPIC": 45, "LEGENDARY": 25},
        "team_card_chance": 15,
        "grants_permanent": True,
        "guarantees_goalkeeper": False,
    },
]


async def seed_packs(db: AsyncSession) -> int:
    """Idempotent: packs are keyed by id and refreshed to match the definition."""
    created = 0
    for spec in DEFAULT_PACKS:
        pack = await db.get(Pack, spec["id"])
        if pack is None:
            pack = Pack(**spec)
            db.add(pack)
            created += 1
        else:
            for key, value in spec.items():
                setattr(pack, key, value)
    await db.commit()
    return created


async def has_catalog(db: AsyncSession) -> bool:
    from app.models import Player

    return bool(await db.scalar(select(func.count()).select_from(Player)))
