from __future__ import annotations

import collections
import hashlib
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import RATINGS
from app.models import Match, MatchStatus, Player, Position, Team

ATTRS = tuple(RATINGS["attributes"])
SCALE_MIN = RATINGS["scaleMin"]
SCALE_MAX = RATINGS["scaleMax"]
ATTACK_SHIRTS = set(RATINGS["attackShirts"])
DEFENCE_SHIRTS = set(RATINGS["defenceShirts"])
SHIRT_BONUS = RATINGS["shirtBonus"]
ROUND_DEPTH = RATINGS["roundDepth"]
CUTOFFS = RATINGS["rarityRankCutoffs"]

# Deterministic palette so a team keeps its colour between syncs.
PALETTE = [
    "#4f7cff", "#ff5c6c", "#33d69f", "#ffb648", "#b366ff", "#3ec8e0",
    "#ff8a5c", "#7ee081", "#f45cc0", "#5c8dff", "#e0c33e", "#57d1a8",
    "#ff6f91", "#8a7bff", "#4bb3fd", "#ffa14a",
]


def round_depth(label: str | None) -> int:
    low = (label or "").lower()
    for key, weight in ROUND_DEPTH.items():
        if key in low:
            return int(weight)
    return 1


def scale(value: float, low: float, high: float) -> int:
    """Min-max normalisation of a raw metric onto the rating scale."""
    if high <= low:
        return (SCALE_MIN + SCALE_MAX) // 2
    ratio = max(0.0, min(1.0, (value - low) / (high - low)))
    return int(round(SCALE_MIN + ratio * (SCALE_MAX - SCALE_MIN)))


def team_color(external_id: str) -> str:
    digest = hashlib.sha1(external_id.encode()).digest()
    return PALETTE[digest[0] % len(PALETTE)]


def age_on(dob: date | None, today: date) -> float:
    if dob is None:
        return 25.0
    return (today - dob).days / 365.25


class RatingService:
    """Turns real match results into card ratings.

    GoFuture publishes no per-player statistics, so every attribute is derived
    from what the team actually did in the tournament (goals in the digital and
    physical legs, shootouts, how deep it went in the bracket) and then shaded
    per player by the two personal facts the API does provide: shirt number and
    date of birth.
    """

    def __init__(self, db: AsyncSession, today: date | None = None) -> None:
        self.db = db
        self.today = today or date.today()

    async def _collect_team_stats(self) -> dict[int, collections.Counter]:
        stats: dict[int, collections.Counter] = collections.defaultdict(collections.Counter)
        matches = await self.db.scalars(
            select(Match).where(Match.status == MatchStatus.COMPLETED)
        )
        for match in matches:
            depth = round_depth(match.round_label)
            sides = (
                (match.home_team_id, "home", "away"),
                (match.away_team_id, "away", "home"),
            )
            for team_id, own, opp in sides:
                if team_id is None:
                    continue
                s = stats[team_id]
                s["played"] += 1
                s["gf"] += getattr(match, f"{own}_score")
                s["ga"] += getattr(match, f"{opp}_score")
                s["dig_f"] += getattr(match, f"{own}_digital")
                s["dig_a"] += getattr(match, f"{opp}_digital")
                s["phy_f"] += getattr(match, f"{own}_physical")
                s["phy_a"] += getattr(match, f"{opp}_physical")

                own_so = getattr(match, f"{own}_shootouts")
                opp_so = getattr(match, f"{opp}_shootouts")
                if own_so or opp_so:
                    s["so_played"] += 1
                    s["so_won"] += 1 if own_so > opp_so else 0

                if match.winner_team_id == team_id:
                    s["won"] += 1
                elif match.winner_team_id is None:
                    s["drawn"] += 1
                else:
                    s["lost"] += 1

                s["best_round"] = max(s["best_round"], depth)
        return stats

    @staticmethod
    def _raw_metrics(s: collections.Counter) -> dict[str, float]:
        played = max(s["played"], 1)
        return {
            "atk": s["gf"] / played,
            "def": -(s["ga"] / played),
            "dig": (s["dig_f"] - s["dig_a"]) / played,
            "phy": (s["phy_f"] - s["phy_a"]) / played,
            "clt": (s["so_won"] / s["so_played"] if s["so_played"] else 0.4) + s["best_round"] / 6,
            "exp": s["played"] + s["best_round"],
        }

    def _apply(self, target, attrs: dict[str, int], stats: collections.Counter, ovr: int) -> None:
        target.atk = attrs["atk"]
        target.deff = attrs["def"]
        target.dig = attrs["dig"]
        target.phy = attrs["phy"]
        target.clt = attrs["clt"]
        target.exp = attrs["exp"]
        target.ovr = ovr
        target.matches_played = stats["played"]
        target.wins = stats["won"]
        target.draws = stats["drawn"]
        target.losses = stats["lost"]
        target.goals_for = stats["gf"]
        target.goals_against = stats["ga"]
        target.best_round = stats["best_round"]

    async def recompute(self) -> dict:
        stats = await self._collect_team_stats()
        teams = list(await self.db.scalars(select(Team)))
        rated = [t for t in teams if stats.get(t.id, collections.Counter())["played"]]

        if not rated:
            return {"teams": 0, "players": 0, "note": "нет завершённых матчей"}

        raw = {t.id: self._raw_metrics(stats[t.id]) for t in rated}
        bounds = {
            key: (min(v[key] for v in raw.values()), max(v[key] for v in raw.values()))
            for key in ATTRS
        }
        team_attrs = {
            tid: {key: scale(metrics[key], *bounds[key]) for key in ATTRS}
            for tid, metrics in raw.items()
        }

        w_team = RATINGS["weightsField"]
        for team in teams:
            if not team.color:
                team.color = team_color(team.external_id)
            attrs = team_attrs.get(team.id)
            if attrs is None:
                continue
            ovr = int(round(sum(attrs[k] * w_team[k] for k in w_team)))
            self._apply(team, attrs, stats[team.id], ovr)

        for index, team in enumerate(sorted(rated, key=lambda t: -t.ovr), start=1):
            team.rank = index

        players = list(await self.db.scalars(select(Player)))
        ages = [age_on(p.date_of_birth, self.today) for p in players]
        age_low, age_high = (min(ages), max(ages)) if ages else (20.0, 40.0)

        rated_players: list[Player] = []
        for player, age in zip(players, ages):
            attrs = team_attrs.get(player.team_id or -1)
            if attrs is None:
                player.ovr = 0
                player.rank = None
                continue

            attrs = dict(attrs)
            is_keeper = player.position == Position.GOALKEEPER
            number = player.jersey_number or 0
            if number in ATTACK_SHIRTS:
                attrs["atk"] = min(99, attrs["atk"] + SHIRT_BONUS)
            if is_keeper or number in DEFENCE_SHIRTS:
                attrs["def"] = min(99, attrs["def"] + SHIRT_BONUS)
            # experience blends how far the team went with how long the athlete
            # has been around
            attrs["exp"] = min(
                99, int(round(attrs["exp"] * 0.6 + scale(age, age_low, age_high) * 0.4))
            )

            weights = RATINGS["weightsGoalkeeper"] if is_keeper else RATINGS["weightsField"]
            ovr = int(round(sum(attrs[k] * weights[k] for k in weights)))
            self._apply(player, attrs, stats[player.team_id], ovr)
            rated_players.append(player)

        # ties broken by name so the ranking is stable between syncs
        for index, player in enumerate(
            sorted(rated_players, key=lambda p: (-p.ovr, p.nickname.lower())), start=1
        ):
            player.rank = index

        await self.db.commit()
        return {
            "teams": len(rated),
            "players": len(rated_players),
            "top_ovr": max((p.ovr for p in rated_players), default=0),
        }


def rarities_for_rank(rank: int | None) -> list[str]:
    """Scarcity follows the ranking: only the very best players exist as
    legendary cards, everyone has a common one."""
    tiers = ["COMMON"]
    if rank is None:
        return tiers
    if rank <= CUTOFFS["RARE"]:
        tiers.append("RARE")
    if rank <= CUTOFFS["EPIC"]:
        tiers.append("EPIC")
    if rank <= CUTOFFS["LEGENDARY"]:
        tiers.append("LEGENDARY")
    return tiers
