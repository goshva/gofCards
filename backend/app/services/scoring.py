from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import RARITY_MULTIPLIERS, SCORING, SQUAD_RULES
from app.core.exceptions import NotFound
from app.models import (
    Match,
    MatchStatus,
    PlayerMatchStat,
    PointsHistory,
    Position,
    SquadEntry,
    User,
)
from app.services import catalog
from app.services.squad_service import SquadService


class ScoringService:
    """Points come from two layers.

    Base layer: the team-level match result, which the GoFuture API does provide
    (digital / physical / shootouts legs, winner). Every carded player of a team
    inherits it.

    Detail layer: per-player numbers an admin entered (goals, assists, saves,
    cards). Absent, only the base layer applies.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.squads = SquadService(db)

    def _team_side(self, match: Match, team_id: int | None) -> str | None:
        if team_id is None:
            return None
        if team_id == match.home_team_id:
            return "home"
        if team_id == match.away_team_id:
            return "away"
        return None

    def _team_points(self, match: Match, side: str, position: Position) -> tuple[int, dict[str, int]]:
        own, opp = (
            (match.home_score, match.away_score) if side == "home" else (match.away_score, match.home_score)
        )
        own_digital = match.home_digital if side == "home" else match.away_digital
        own_physical = match.home_physical if side == "home" else match.away_physical
        own_so = match.home_shootouts if side == "home" else match.away_shootouts
        opp_so = match.away_shootouts if side == "home" else match.home_shootouts

        parts: dict[str, int] = {"appearance": SCORING["appearance"]}
        if own > opp:
            parts["win"] = SCORING["win"]
        elif own == opp:
            parts["draw"] = SCORING["draw"]

        if own_digital:
            parts["team_goals_digital"] = own_digital * SCORING["teamGoalDigital"]
        if own_physical:
            parts["team_goals_physical"] = own_physical * SCORING["teamGoalPhysical"]

        if opp == 0:
            parts["clean_sheet"] = (
                SCORING["cleanSheetGoalkeeper"]
                if position == Position.GOALKEEPER
                else SCORING["cleanSheetFieldPlayer"]
            )
        elif position == Position.GOALKEEPER:
            parts["goals_conceded"] = opp * SCORING["goalConcededGoalkeeperPer"]

        if own_so or opp_so:
            parts["shootouts"] = SCORING["shootoutWin"] if own_so > opp_so else SCORING["shootoutLoss"]

        return sum(parts.values()), parts

    def _stat_points(self, stat: PlayerMatchStat, position: Position) -> tuple[int, dict[str, int]]:
        parts: dict[str, int] = {}
        if stat.goals:
            per = (
                SCORING["goalScoredGoalkeeper"]
                if position == Position.GOALKEEPER
                else SCORING["goalScoredFieldPlayer"]
            )
            parts["goals"] = stat.goals * per
        if stat.assists:
            parts["assists"] = stat.assists * SCORING["assist"]
        if stat.saves:
            parts["saves"] = stat.saves * SCORING["save"]
        if stat.own_goals:
            parts["own_goals"] = stat.own_goals * SCORING["ownGoal"]
        if stat.yellow_cards:
            parts["yellow_cards"] = stat.yellow_cards * SCORING["yellowCard"]
        if stat.red_cards:
            parts["red_cards"] = stat.red_cards * SCORING["redCard"]
        return sum(parts.values()), parts

    async def calculate_match_points(self, user: User, match: Match) -> tuple[int, dict, bool]:
        entries = await self.squads.get_entries(user.id, match.id)
        if not entries:
            entries = await self.squads.get_entries(user.id, None)

        stats = {
            s.player_id: s
            for s in await self.db.scalars(
                select(PlayerMatchStat).where(PlayerMatchStat.match_id == match.id)
            )
        }
        templates = await catalog.load_templates(
            self.db,
            [(e.card.card_type, e.card.card_template_id) for e in entries if e.card is not None],
        )

        # Standard fantasy rule: if the captain did not take part in this match,
        # the vice-captain is promoted instead of the multiplier being wasted.
        captain = next((e for e in entries if e.is_captain and e.player is not None), None)
        captain_played = captain is not None and self._team_side(match, captain.player.team_id) is not None

        total = 0
        breakdown: dict[str, dict] = {"players": {}}

        for entry in entries:
            if not entry.is_starter or entry.player is None:
                continue
            side = self._team_side(match, entry.player.team_id)
            if side is None:
                # the carded player did not take part in this match
                continue

            position = entry.player.position
            points, parts = self._team_points(match, side, position)

            stat = stats.get(entry.player_id)
            if stat is not None:
                if not stat.started:
                    parts.pop("appearance", None)
                    points = sum(parts.values())
                extra, extra_parts = self._stat_points(stat, position)
                points += extra
                parts.update(extra_parts)

            rarity_mult = 1.0
            tpl = templates.get((entry.card.card_type, entry.card.card_template_id)) if entry.card else None
            if tpl is not None:
                rarity_mult = RARITY_MULTIPLIERS[tpl.rarity.value]

            captain_mult = 1.0
            if entry.is_captain:
                captain_mult = SQUAD_RULES["captainMultiplier"]
            elif entry.is_vice_captain and not captain_played:
                captain_mult = SQUAD_RULES["viceCaptainMultiplier"]

            final = int(round(points * rarity_mult * captain_mult))
            total += final
            breakdown["players"][str(entry.player_id)] = {
                "nickname": entry.player.nickname,
                "slot": entry.position_slot.value,
                "base": points,
                "rarity": tpl.rarity.value if tpl else None,
                "rarity_multiplier": rarity_mult,
                "captain_multiplier": captain_mult,
                "points": final,
                "parts": parts,
            }

        comparison = await self.squads.compare_perfect_five(user, match.id)
        is_perfect = comparison.is_perfect
        if is_perfect:
            total += SCORING["perfectFiveBonus"]
            breakdown["perfect_five_bonus"] = SCORING["perfectFiveBonus"]
            breakdown["perfect_five_team"] = comparison.matched_team

        breakdown["total"] = total
        return total, breakdown, is_perfect

    async def settle_match(self, match_id: int, force: bool = False) -> dict:
        """Award points to every user who fielded a squad for a finished match.

        Idempotent: an existing PointsHistory row is rewritten and the delta is
        applied to the user total, so a re-run never double-counts.
        """
        match = await self.db.get(Match, match_id)
        if match is None:
            raise NotFound("Матч не найден")
        if match.status != MatchStatus.COMPLETED:
            return {"match_id": match_id, "skipped": "матч не завершён", "users": 0}
        if match.points_calculated and not force:
            return {"match_id": match_id, "skipped": "очки уже начислены", "users": 0}

        # Users who locked a squad for this match, plus everyone whose working
        # draft stands in for one. calculate_match_points prefers the locked
        # snapshot per user, so the union never double-counts.
        user_ids = set(
            await self.db.scalars(
                select(SquadEntry.user_id).where(SquadEntry.match_id == match_id)
            )
        )
        user_ids |= set(
            await self.db.scalars(
                select(SquadEntry.user_id).where(SquadEntry.match_id.is_(None))
            )
        )

        settled = 0
        perfect = 0
        for user_id in user_ids:
            user = await self.db.get(User, user_id)
            if user is None:
                continue
            points, breakdown, is_perfect = await self.calculate_match_points(user, match)

            existing = await self.db.scalar(
                select(PointsHistory).where(
                    PointsHistory.user_id == user_id, PointsHistory.match_id == match_id
                )
            )
            previous = existing.points if existing else 0
            if existing is None:
                existing = PointsHistory(user_id=user_id, match_id=match_id, points=points, breakdown=breakdown, is_perfect_xi=is_perfect)
                self.db.add(existing)
            else:
                existing.points = points
                existing.breakdown = breakdown
                existing.is_perfect_xi = is_perfect

            user.total_points += points - previous
            settled += 1
            perfect += 1 if is_perfect else 0

        match.points_calculated = True
        await self.db.commit()
        return {"match_id": match_id, "users": settled, "perfect_fives": perfect}

    async def settle_pending(self) -> dict:
        matches = await self.db.scalars(
            select(Match).where(
                Match.status == MatchStatus.COMPLETED, Match.points_calculated.is_(False)
            )
        )
        results = [await self.settle_match(m.id) for m in matches]
        return {
            "matches": len(results),
            "users": sum(r.get("users", 0) for r in results),
            "details": results,
        }
