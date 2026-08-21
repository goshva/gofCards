"""Loads the shared constants file so backend and frontend never drift apart."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_SHARED = Path(__file__).resolve().parents[3] / "shared" / "constants.json"


@lru_cache(maxsize=1)
def shared_constants() -> dict[str, Any]:
    with _SHARED.open(encoding="utf-8") as fh:
        return json.load(fh)


CONST = shared_constants()

RARITY_WEIGHTS: dict[str, int] = CONST["rarityWeights"]
RARITY_MULTIPLIERS: dict[str, float] = CONST["rarityMultipliers"]
RARITY_BASE_PRICE: dict[str, int] = CONST["rarityBasePrice"]
SQUAD_RULES: dict[str, Any] = CONST["squadRules"]
SCORING: dict[str, int] = CONST["scoring"]
GOFUTURE: dict[str, str] = CONST["gofuture"]
STARTING_COINS: int = CONST["startingCoins"]
RATINGS: dict[str, Any] = CONST["ratings"]
TOURNAMENT: dict[str, Any] = CONST["tournament"]
CARDS: dict[str, Any] = CONST["cards"]
TOURNAMENT_LIFESPAN: int = CARDS["tournamentLifespan"]
PAYMENTS: dict[str, Any] = CONST["payments"]
QUESTS: dict[str, Any] = CONST["quests"]
