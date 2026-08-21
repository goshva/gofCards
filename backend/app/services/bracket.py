from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Match, MatchStatus


@dataclass(frozen=True)
class Slot:
    """Where a participant of a match comes from.

    kind is either "seed" (the team entered the tournament here) or
    "winner"/"loser" of an earlier match.
    """

    kind: str
    team_id: int | None = None
    source_match: int | None = None

    @property
    def is_seed(self) -> bool:
        return self.kind == "seed"


@dataclass
class BracketMatch:
    id: int
    slug: str
    order: int
    label: str
    home: Slot
    away: Slot
    real_home_id: int | None
    real_away_id: int | None
    real_winner_id: int | None
    real_home_score: int
    real_away_score: int
    knockout: bool


@dataclass
class Bracket:
    matches: list[BracketMatch] = field(default_factory=list)

    @property
    def seeds(self) -> list[int]:
        seen: list[int] = []
        for match in self.matches:
            for slot in (match.home, match.away):
                if slot.is_seed and slot.team_id is not None and slot.team_id not in seen:
                    seen.append(slot.team_id)
        return seen

    def last_match_of(self, team_id: int) -> BracketMatch | None:
        played = [m for m in self.matches if team_id in (m.real_home_id, m.real_away_id)]
        return played[-1] if played else None


KNOCKOUT_MARKERS = ("decider", "last 16", "qf", "sf", "final", "3rd place")


def is_knockout(label: str | None) -> bool:
    low = (label or "").lower()
    return any(marker in low for marker in KNOCKOUT_MARKERS)


async def build_bracket(db: AsyncSession, tournament_slug: str) -> Bracket:
    """Reconstruct the bracket graph from the real fixtures.

    Nothing about the format is hard-coded. For every participant the previous
    match it appeared in is located, which says whether it arrived there as a
    winner or as a loser; a team with no earlier match is a seed. That derives
    the GSL groups, the cross-group deciders and the playoff tree straight from
    the data, and works unchanged for a differently shaped tournament.
    """
    matches = list(
        await db.scalars(
            select(Match)
            .where(
                Match.tournament_slug == tournament_slug,
                Match.status == MatchStatus.COMPLETED,
            )
            .order_by(Match.round, Match.id)
        )
    )

    bracket = Bracket()
    history: dict[int, BracketMatch] = {}

    for order, match in enumerate(matches):
        def slot_for(team_id: int | None) -> Slot:
            if team_id is None:
                return Slot(kind="seed")
            previous = history.get(team_id)
            if previous is None:
                return Slot(kind="seed", team_id=team_id)
            kind = "winner" if previous.real_winner_id == team_id else "loser"
            return Slot(kind=kind, source_match=previous.id)

        entry = BracketMatch(
            id=match.id,
            slug=match.slug,
            order=order,
            label=match.round_label or match.slug,
            home=slot_for(match.home_team_id),
            away=slot_for(match.away_team_id),
            real_home_id=match.home_team_id,
            real_away_id=match.away_team_id,
            real_winner_id=match.winner_team_id,
            real_home_score=match.home_score,
            real_away_score=match.away_score,
            knockout=is_knockout(match.round_label),
        )
        bracket.matches.append(entry)

        for team_id in (match.home_team_id, match.away_team_id):
            if team_id is not None:
                history[team_id] = entry

    return bracket
