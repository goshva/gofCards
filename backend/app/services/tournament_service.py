from __future__ import annotations

import math
import random
import secrets
from dataclasses import dataclass
from datetime import timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import SQUAD_RULES, TOURNAMENT, TOURNAMENT_LIFESPAN
from app.core.exceptions import AlreadyExists, InsufficientFunds, InvalidSquad, NotFound
from app.models import SquadEntry, Team, TournamentEntry, User, UserCard
from app.models.base import utcnow
from app.services import catalog
from app.services.bracket import Bracket, BracketMatch, build_bracket
from app.services.squad_service import SquadService

USER_SIDE = "USER"

STAGE_ORDER: list[str] = TOURNAMENT["stageOrder"]
ELO_DIVISOR = float(TOURNAMENT["eloDivisor"])
DRAW_BASE = float(TOURNAMENT["drawBase"])
DRAW_FALLOFF = float(TOURNAMENT["drawFalloff"])
BASE_GOALS = float(TOURNAMENT["baseGoals"])
MAX_GOALS = int(TOURNAMENT["maxGoals"])


def win_probability(own_ovr: float, opponent_ovr: float) -> float:
    """Logistic curve on the rating gap, the same shape Elo uses.

    A 14-point edge is roughly a 3-to-1 favourite; equal ratings are a coin
    flip. Nothing tilts the curve toward the player.
    """
    return 1.0 / (1.0 + math.pow(10.0, (opponent_ovr - own_ovr) / ELO_DIVISOR))


def draw_probability(own_ovr: float, opponent_ovr: float) -> float:
    gap = abs(own_ovr - opponent_ovr)
    return DRAW_BASE * max(0.0, 1.0 - gap / DRAW_FALLOFF)


@dataclass
class Side:
    key: object  # a team id, or USER_SIDE
    name: str
    ovr: int
    is_user: bool = False


class DrawMachine:
    """Every random decision of a run comes from here.

    It is seeded once per entry and the seed is stored with the result, so the
    same entry always replays identically and anyone can check the run was not
    tilted afterwards.
    """

    def __init__(self, seed: str) -> None:
        self.seed = seed
        self.rng = random.Random(int(seed, 16))

    def wins(self, own: float, opponent: float) -> bool:
        """Every match in this tournament is decisive — a level score goes to
        shootouts — so the draw only ever picks a winner."""
        return self.rng.random() < win_probability(own, opponent)

    def scoreline(self, winner_ovr: float, loser_ovr: float) -> tuple[int, int, tuple[int, int] | None]:
        """A plausible score for a result the draw has already decided.

        Settling the winner first and dressing the score afterwards keeps the
        published odds exactly honest: a scoreline can never contradict the
        probability the player was shown.
        """
        edge = (winner_ovr - loser_ovr) / 40.0
        strong = max(0.6, BASE_GOALS * (1.0 + edge))
        weak = max(0.4, BASE_GOALS * (1.0 - edge))

        # a quarter of the real matches ended level and went to shootouts,
        # and that happens more often between evenly matched sides
        if self.rng.random() < draw_probability(winner_ovr, loser_ovr):
            level = min(MAX_GOALS, max(0, int(round(self.rng.gauss((strong + weak) / 2, 0.9)))))
            return level, level, self.shootout()

        winner_goals = min(MAX_GOALS, max(1, int(round(self.rng.gauss(strong + 0.7, 1.1)))))
        loser_goals = max(0, min(int(round(self.rng.gauss(weak - 0.4, 0.9))), winner_goals - 1))
        return winner_goals, loser_goals, None

    def shootout(self) -> tuple[int, int]:
        winner = self.rng.randint(3, 5)
        return winner, self.rng.randint(0, winner - 1)

    def split_legs(self, goals: int) -> tuple[int, int]:
        """Phygital football is played as a digital half and a physical half."""
        digital = self.rng.randint(0, goals)
        return digital, goals - digital


class TournamentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.squads = SquadService(db)

    async def squad_strength(self, user: User) -> tuple[int, list[dict]]:
        """Rating of the fielded five, with the captain counting double.

        Nothing stops a card of a player who also turns out for a real team in
        this bracket: the same athlete can line up on both sides.
        """
        entries = await self.squads.get_entries(user.id, None)
        starters = [e for e in entries if e.is_starter]
        if len(starters) != SQUAD_RULES["starters"]:
            raise InvalidSquad(
                f"Нужна полная стартовая пятёрка: заполнено {len(starters)} из {SQUAD_RULES['starters']}"
            )
        if not any(e.is_captain for e in starters):
            raise InvalidSquad("Не назначен капитан")

        cards = [e.card for e in starters if e.card is not None]
        templates = await catalog.load_templates(
            self.db, [(c.card_type, c.card_template_id) for c in cards]
        )

        weighted = 0.0
        total_weight = 0.0
        roster: list[dict] = []
        captain_weight = float(TOURNAMENT["captainWeight"])
        for entry in starters:
            card = entry.card
            tpl = templates.get((card.card_type, card.card_template_id)) if card else None
            ovr = tpl.ovr if tpl else 0
            weight = captain_weight if entry.is_captain else 1.0
            weighted += ovr * weight
            total_weight += weight
            roster.append(
                {
                    "user_card_id": card.id if card else None,
                    "is_permanent": bool(card and card.is_permanent),
                    "runs_left": card.runs_left if card else None,
                    "slot": entry.position_slot.value,
                    "player_id": entry.player_id,
                    "nickname": entry.player.nickname if entry.player else "",
                    "team": entry.player.team.title if entry.player and entry.player.team else None,
                    "rarity": tpl.rarity.value if tpl else None,
                    "ovr": ovr,
                    "is_captain": entry.is_captain,
                }
            )

        return int(round(weighted / total_weight)) if total_weight else 0, roster

    async def _wear_down(self, roster: list[dict]) -> list[dict]:
        """Spend one run of every card that was fielded.

        A permanent card is untouched. An ordinary one is discarded once its
        sixth tournament is behind it, and disappears from the squad with it.
        """
        retired: list[dict] = []
        for slot in roster:
            card_id = slot.get("user_card_id")
            if not card_id:
                continue
            card = await self.db.get(UserCard, card_id)
            if card is None or card.is_permanent:
                slot["runs_left"] = None if card and card.is_permanent else slot.get("runs_left")
                continue

            card.tournaments_used += 1
            slot["runs_left"] = card.runs_left
            if card.runs_left <= 0:
                retired.append(
                    {"nickname": slot.get("nickname"), "ovr": slot.get("ovr"), "slot": slot.get("slot")}
                )
                entries = await self.db.scalars(
                    select(SquadEntry).where(SquadEntry.user_card_id == card.id)
                )
                for entry in entries:
                    await self.db.delete(entry)
                await self.db.delete(card)
        return retired

    async def weakest_team(self, tournament_slug: str) -> Team:
        """The slot the user takes over: the lowest rated side that actually played."""
        team = await self.db.scalar(
            select(Team)
            .where(Team.matches_played > 0)
            .order_by(Team.ovr.asc(), Team.goals_for.asc(), Team.id.asc())
            .limit(1)
        )
        if team is None:
            raise NotFound("Нет команд с результатами — сначала выполните синхронизацию")
        return team

    def _stage_of(self, label: str) -> str:
        low = label.lower()
        if "final" in low:
            return "MEDAL"
        if "3rd place" in low:
            return "MEDAL"
        if "sf" in low:
            return "SEMI"
        if "qf" in low:
            return "QUARTER"
        if "decider" in low or "last 16" in low:
            return "DECIDER"
        return "GROUP"

    def _play(
        self,
        draw: DrawMachine,
        match: BracketMatch,
        home: Side,
        away: Side,
    ) -> dict:
        """Resolve one fixture.

        A pairing that still matches history keeps its real result, so the rest
        of the bracket stays exactly as it was played; only the fixtures the
        substituted squad touches, and whatever they knock out of shape
        downstream, are decided by the draw.
        """
        faithful = (
            not home.is_user
            and not away.is_user
            and home.key == match.real_home_id
            and away.key == match.real_away_id
        )
        if faithful:
            home_goals, away_goals = match.real_home_score, match.real_away_score
            winner_key = match.real_winner_id
            shootout = None
            source = "real"
        else:
            home_wins = draw.wins(home.ovr, away.ovr)
            winner, loser = (home, away) if home_wins else (away, home)
            w_goals, l_goals, shootout = draw.scoreline(winner.ovr, loser.ovr)
            home_goals, away_goals = (w_goals, l_goals) if home_wins else (l_goals, w_goals)
            winner_key = winner.key
            source = "simulated"

        winner_side = home if winner_key == home.key else away
        loser_side = away if winner_side is home else home
        home_digital, home_physical = draw.split_legs(home_goals)
        away_digital, away_physical = draw.split_legs(away_goals)

        return {
            "match_id": match.id,
            "label": match.label,
            "stage": self._stage_of(match.label),
            "source": source,
            "home": {"name": home.name, "ovr": home.ovr, "is_user": home.is_user},
            "away": {"name": away.name, "ovr": away.ovr, "is_user": away.is_user},
            "home_score": home_goals,
            "away_score": away_goals,
            "digital": [home_digital, away_digital],
            "physical": [home_physical, away_physical],
            "shootout": list(shootout) if shootout else None,
            "winner": winner_side.name,
            "winner_key": winner_side.key,
            "loser_key": loser_side.key,
            "user_involved": home.is_user or away.is_user,
            "user_won": winner_side.is_user,
            "user_win_chance": (
                round(win_probability(home.ovr, away.ovr), 3)
                if home.is_user
                else round(win_probability(away.ovr, home.ovr), 3)
                if away.is_user
                else None
            ),
        }

    async def _run_bracket(
        self, bracket: Bracket, replaced: Team, squad_ovr: int, draw: DrawMachine
    ) -> list[dict]:
        teams = {t.id: t for t in await self.db.scalars(select(Team))}
        resolved: dict[int, dict] = {}

        def side(key) -> Side:
            if key == USER_SIDE:
                return Side(key=USER_SIDE, name="Ваша команда", ovr=squad_ovr, is_user=True)
            team = teams.get(key)
            return Side(key=key, name=team.title if team else "TBD", ovr=team.ovr if team else 0)

        def resolve(slot) -> object | None:
            if slot.is_seed:
                if slot.team_id is None:
                    return None
                # the substitution happens here and then simply propagates
                return USER_SIDE if slot.team_id == replaced.id else slot.team_id
            previous = resolved.get(slot.source_match)
            if previous is None:
                return None
            return previous["winner_key"] if slot.kind == "winner" else previous["loser_key"]

        log: list[dict] = []
        for match in bracket.matches:
            home_key = resolve(match.home)
            away_key = resolve(match.away)
            if home_key is None or away_key is None:
                continue
            result = self._play(draw, match, side(home_key), side(away_key))
            resolved[match.id] = result
            log.append(result)
        return log

    @staticmethod
    def _summarise(log: list[dict]) -> dict:
        own = [m for m in log if m["user_involved"]]
        wins = sum(1 for m in own if m["user_won"])
        deepest = "NONE"
        for m in own:
            if STAGE_ORDER.index(m["stage"]) > STAGE_ORDER.index(deepest):
                deepest = m["stage"]

        # winning the last match of the bracket is the title itself
        champion = any(
            m["user_won"] and m["label"].lower().strip() == "final" for m in own
        )
        stage = "CHAMPION" if champion else deepest
        return {
            "stage": stage,
            "stage_index": STAGE_ORDER.index(stage),
            "played": len(own),
            "wins": wins,
            "losses": len(own) - wins,
            "matches": own,
        }

    async def preview(self, user: User, tournament_slug: str) -> dict:
        """What the run would look like before paying the entry fee."""
        squad_ovr, roster = await self.squad_strength(user)
        replaced = await self.weakest_team(tournament_slug)
        first = None
        bracket = await build_bracket(self.db, tournament_slug)
        for match in bracket.matches:
            if replaced.id in (match.real_home_id, match.real_away_id):
                opponent_id = (
                    match.real_away_id if match.real_home_id == replaced.id else match.real_home_id
                )
                opponent = await self.db.get(Team, opponent_id) if opponent_id else None
                first = {
                    "label": match.label,
                    "opponent": opponent.title if opponent else "TBD",
                    "opponent_ovr": opponent.ovr if opponent else 0,
                    "win_chance": round(win_probability(squad_ovr, opponent.ovr), 3) if opponent else None,
                }
                break

        return {
            "tournament_slug": tournament_slug,
            "entry_fee": TOURNAMENT["entryFee"],
            "cooldown_seconds": await self.cooldown_left(user),
            "squad_ovr": squad_ovr,
            "squad": roster,
            "replaced_team": {
                "id": replaced.id,
                "title": replaced.title,
                "ovr": replaced.ovr,
                "rank": replaced.rank,
                "record": f"{replaced.wins}-{replaced.draws}-{replaced.losses}",
            },
            "first_match": first,
            "coins_per_stage": TOURNAMENT["coinsPerStage"],
            "points_per_stage": TOURNAMENT["pointsPerStage"],
        }

    async def cooldown_left(self, user: User) -> int:
        """Seconds until the next run is allowed.

        Without it a strong collection could farm the boost on repeat, so a run
        is gated rather than the reward being watered down.
        """
        minutes = int(TOURNAMENT.get("cooldownMinutes", 0))
        if minutes <= 0:
            return 0
        last = await self.db.scalar(
            select(TournamentEntry)
            .where(TournamentEntry.user_id == user.id)
            .order_by(TournamentEntry.created_at.desc())
            .limit(1)
        )
        if last is None:
            return 0
        # sqlite hands timestamps back without a timezone, so pin them to UTC
        # before doing arithmetic against an aware "now"
        stamped = last.created_at
        if stamped.tzinfo is None:
            stamped = stamped.replace(tzinfo=timezone.utc)
        ready_at = stamped + timedelta(minutes=minutes)
        return max(0, int((ready_at - utcnow()).total_seconds()))

    async def enter(self, user: User, tournament_slug: str, seed: str | None = None) -> TournamentEntry:
        wait = await self.cooldown_left(user)
        if wait:
            raise AlreadyExists(f"Следующая попытка будет доступна через {wait // 60 + 1} мин")

        fee = int(TOURNAMENT["entryFee"])
        if user.coins < fee:
            raise InsufficientFunds(f"Взнос {fee} монет, доступно {user.coins}")

        squad_ovr, roster = await self.squad_strength(user)
        replaced = await self.weakest_team(tournament_slug)
        bracket = await build_bracket(self.db, tournament_slug)
        if not bracket.matches:
            raise NotFound("Сетка турнира пуста")

        draw = DrawMachine(seed or secrets.token_hex(8))
        log = await self._run_bracket(bracket, replaced, squad_ovr, draw)
        summary = self._summarise(log)

        coins = summary["stage_index"] * int(TOURNAMENT["coinsPerStage"]) + summary["wins"] * int(
            TOURNAMENT["winBonusCoins"]
        )
        points = summary["stage_index"] * int(TOURNAMENT["pointsPerStage"]) + summary["wins"] * int(
            TOURNAMENT["winBonusPoints"]
        )

        user.coins += coins - fee
        user.total_points += points
        retired = await self._wear_down(roster)

        entry = TournamentEntry(
            user_id=user.id,
            tournament_slug=tournament_slug,
            seed=draw.seed,
            replaced_team_id=replaced.id,
            squad_ovr=squad_ovr,
            squad_json=roster,
            stage=summary["stage"],
            stage_index=summary["stage_index"],
            played=summary["played"],
            wins=summary["wins"],
            draws=0,
            losses=summary["losses"],
            entry_fee=fee,
            coins_awarded=coins,
            points_awarded=points,
            run_json=log,
            retired_json=retired,
            finished_at=utcnow(),
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry
